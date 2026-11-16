"""One-use action challenge fixture with real session/TOTP verification.

Test-only: no production route, recovery codes, migration, real CSRF/rate-limit
middleware, durable intent/audit, or provider dispatch. auth.session must be
bound to this disposable engine. Existing older fixture issuers are not this
challenge flow and are not production entry points.
"""
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone

from sqlalchemy import text

from crownpath import auth
from tests.payment_action_binding_fixture import action_digest, _proof_hash
from tests.payment_real_stepup_fixture import ORIGIN, _claims, _lock_live_scope, _begin_sqlite_write

_PENDING = """
    challenge_hash=:challenge AND user_id=:user_id AND session_id=:session_id
    AND action_digest=:action AND consumed_at IS NULL AND expires_at>:now
    AND failed_attempts>=0 AND failed_attempts<5
"""


def _now():
    return int(datetime.now(timezone.utc).timestamp())


def _challenge_hash(token):
    return hmac.new(
        auth.SECRET_KEY.encode(), ("payment-action-challenge:" + token).encode(),
        hashlib.sha256,
    ).hexdigest()


def create_action_challenge_test_schema(engine):
    with engine.begin() as db:
        db.execute(text("""
            CREATE TABLE payment_action_challenges_test (
                challenge_hash VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                session_id VARCHAR(128) NOT NULL,
                action_digest VARCHAR(64) NOT NULL,
                expires_at BIGINT NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                consumed_at BIGINT
            )
        """))


def create_action_challenge(engine, *, cookie, action, origin):
    if origin != ORIGIN:
        return None
    try:
        digest = action_digest(action)
    except ValueError:
        return None
    claims = _claims(cookie)
    if claims is None:
        return None
    now = _now()
    challenge = secrets.token_urlsafe(32)
    with engine.begin() as db:
        _begin_sqlite_write(db)
        if not _lock_live_scope(db, claims, now):
            return None
        db.execute(text("""
            INSERT INTO payment_action_challenges_test
              (challenge_hash,user_id,session_id,action_digest,expires_at,failed_attempts)
            VALUES (:challenge,:user_id,:session_id,:action,:expiry,0)
        """), {"challenge": _challenge_hash(challenge), "user_id": claims["sub"],
               "session_id": claims["jti"], "action": digest, "expiry": now + 120})
    return challenge


def confirm_action_challenge(engine, *, cookie, challenge, action, code, origin):
    if (origin != ORIGIN or not isinstance(challenge, str) or not challenge
            or not isinstance(code, str) or not re.fullmatch(r"[0-9]{6}", code)):
        return None
    try:
        digest = action_digest(action)
    except ValueError:
        return None
    claims = _claims(cookie)
    if claims is None:
        return None
    values = {"challenge": _challenge_hash(challenge), "user_id": claims["sub"],
              "session_id": claims["jti"], "action": digest, "now": _now()}
    # Do not verify a code for an unrelated or already-closed challenge.
    with engine.begin() as db:
        _begin_sqlite_write(db)
        if not _lock_live_scope(db, claims, values["now"]):
            return None
        pending = db.scalar(text(
            "SELECT challenge_hash FROM payment_action_challenges_test WHERE " + _PENDING
        ), values)
        if pending is None:
            return None
    # The actual verifier updates account lockout state in its own transaction.
    # No scope locks are held while it executes.
    verified = auth.verify_mfa_code(claims["sub"], code)
    values["now"] = _now()
    proof = secrets.token_urlsafe(32)
    with engine.begin() as db:
        _begin_sqlite_write(db)
        if not _lock_live_scope(db, claims, values["now"]):
            return None
        if not verified:
            db.execute(text(
                "UPDATE payment_action_challenges_test "
                "SET failed_attempts=failed_attempts+1 WHERE " + _PENDING
            ), values)
            return None
        claimed = db.execute(text(
            "UPDATE payment_action_challenges_test SET consumed_at=:now WHERE " + _PENDING
        ), values)
        if claimed.rowcount != 1:
            return None
        db.execute(text("""
            INSERT INTO payment_action_bound_proofs_test
                (proof_hash,user_id,session_id,action_digest,expires_at,used_at)
            VALUES (:proof,:user_id,:session_id,:action,:expiry,NULL)
        """), {**values, "proof": _proof_hash(proof, auth.SECRET_KEY.encode()),
               "expiry": values["now"] + 120})
    return proof
