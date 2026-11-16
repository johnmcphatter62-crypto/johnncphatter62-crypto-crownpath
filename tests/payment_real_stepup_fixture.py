"""Isolated adapter for real session/TOTP checks and action-bound test proofs.

NOT a production route or payment service. The caller binds auth.session to the
same disposable engine. Origin is a harness restriction, not full CSRF. Recovery
codes, one-use action challenges, durable intent/audit, and provider delivery are
not implemented here.
"""
import re
import secrets
from datetime import datetime, timezone

import jwt
from sqlalchemy import insert, select, text

from crownpath import auth
from crownpath.models import AuthToken, User
from tests.payment_action_binding_fixture import action_digest, _proof_hash

ORIGIN = "https://testserver"


def _claims(cookie):
    if not isinstance(cookie, str) or not cookie:
        return None
    user_id = auth.decode_access_token(cookie)
    if not user_id or not auth.session_mfa_verified(cookie):
        return None
    try:
        claims = jwt.decode(cookie, auth.SECRET_KEY, algorithms=[auth.ALGORITHM],
                            options={"require": ["sub", "jti", "exp", "iat", "purpose"]})
    except jwt.InvalidTokenError:
        return None
    if claims.get("sub") != user_id or claims.get("purpose") != "session":
        return None
    if not isinstance(claims.get("jti"), str) or not claims["jti"].strip():
        return None
    return claims


def _lock_live_scope(db, claims, now):
    when = datetime.fromtimestamp(now, timezone.utc)
    owner = db.execute(select(User.user_id).where(
        User.user_id == claims["sub"], User.role == "OWNER",
        User.active.is_(True), User.mfa_enabled.is_(True),
    ).with_for_update()).scalar_one_or_none()
    if owner is None:
        return False
    session = db.execute(select(AuthToken.token_id).where(
        AuthToken.user_id == owner,
        AuthToken.token_hash == auth._hash_session_id(claims["jti"]),
        AuthToken.token_type == "SESSION", AuthToken.used_at.is_(None),
        AuthToken.expires_at > when,
    ).with_for_update()).scalar_one_or_none()
    return session is not None


def _begin_sqlite_write(db):
    if db.dialect.name == "sqlite":
        db.exec_driver_sql("BEGIN IMMEDIATE")


def issue_from_real_session(engine, *, cookie, action, code, origin):
    if origin != ORIGIN or not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code):
        return None
    try:
        digest = action_digest(action)
    except ValueError:
        return None
    claims = _claims(cookie)
    if claims is None:
        return None
    user = auth.get_user_by_id(claims["sub"])
    if not user or user["role"] != "OWNER" or not user["active"] or not user["mfa_enabled"]:
        return None
    # Fresh server verification; no client-supplied assurance boolean is accepted.
    if not auth.verify_mfa_code(claims["sub"], code):
        return None
    now = int(datetime.now(timezone.utc).timestamp())
    token = secrets.token_urlsafe(32)
    with engine.begin() as db:
        _begin_sqlite_write(db)
        if not _lock_live_scope(db, claims, now):
            return None
        db.execute(text("""
            INSERT INTO payment_action_bound_proofs_test
                (proof_hash, user_id, session_id, action_digest, expires_at, used_at)
            VALUES (:proof, :user_id, :session_id, :action, :expiry, NULL)
        """), {"proof": _proof_hash(token, auth.SECRET_KEY.encode()),
               "user_id": claims["sub"], "session_id": claims["jti"],
               "action": digest, "expiry": now + 120})
    return token


def consume_from_real_session(engine, *, cookie, proof, action, origin):
    if origin != ORIGIN or not isinstance(proof, str) or not proof:
        return False
    try:
        digest = action_digest(action)
    except ValueError:
        return False
    claims = _claims(cookie)
    if claims is None:
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    with engine.begin() as db:
        _begin_sqlite_write(db)
        if not _lock_live_scope(db, claims, now):
            return False
        result = db.execute(text("""
            UPDATE payment_action_bound_proofs_test SET used_at=:now
            WHERE proof_hash=:proof AND user_id=:user_id AND session_id=:session_id
              AND action_digest=:action AND used_at IS NULL AND expires_at>:now
        """), {"now": now, "proof": _proof_hash(proof, auth.SECRET_KEY.encode()),
               "user_id": claims["sub"], "session_id": claims["jti"], "action": digest})
        return result.rowcount == 1
