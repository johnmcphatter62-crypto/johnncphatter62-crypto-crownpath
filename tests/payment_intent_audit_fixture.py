"""Atomic intent/audit fixture; no provider dispatch or production route."""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone

from sqlalchemy import text

from crownpath import auth
from crownpath.models import AuditEvent
from tests.payment_action_binding_fixture import action_digest, _proof_hash
from tests.payment_real_stepup_fixture import ORIGIN, _claims, _lock_live_scope, _begin_sqlite_write


def create_intent_audit_test_schema(engine):
    AuditEvent.__table__.create(engine, checkfirst=True)
    with engine.begin() as db:
        db.execute(text("""
            CREATE TABLE payment_authorized_intents_test (
                intent_id VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                session_hash VARCHAR(64) NOT NULL,
                proof_hash VARCHAR(64) NOT NULL UNIQUE,
                action_digest VARCHAR(64) NOT NULL,
                action_json TEXT NOT NULL,
                idempotency_key VARCHAR(64) NOT NULL UNIQUE,
                status VARCHAR(16) NOT NULL,
                created_at BIGINT NOT NULL
            )
        """))


def authorize_intent(engine, *, cookie, proof, action, origin):
    if origin != ORIGIN or not isinstance(proof, str) or not proof:
        return None
    try:
        # Persist and authorize the same detached snapshot.
        canonical = json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        digest = action_digest(json.loads(canonical))
    except (ValueError, TypeError):
        return None
    claims = _claims(cookie)
    if claims is None:
        return None
    when = datetime.now(timezone.utc)
    now = int(when.timestamp())
    hashed_proof = _proof_hash(proof, auth.SECRET_KEY.encode())
    values = {
        "proof": hashed_proof, "user_id": claims["sub"],
        "session_id": claims["jti"], "session_hash": auth._hash_session_id(claims["jti"]),
        "action": digest, "now": now,
    }
    with engine.begin() as db:
        _begin_sqlite_write(db)
        if not _lock_live_scope(db, claims, now):
            return None
        existing = db.execute(text("""
            SELECT intent_id,idempotency_key,status FROM payment_authorized_intents_test
            WHERE proof_hash=:proof AND user_id=:user_id
              AND session_hash=:session_hash AND action_digest=:action
        """), values).mappings().one_or_none()
        if existing is not None:
            return dict(existing)
        consumed = db.execute(text("""
            UPDATE payment_action_bound_proofs_test SET used_at=:now
            WHERE proof_hash=:proof AND user_id=:user_id AND session_id=:session_id
              AND action_digest=:action AND used_at IS NULL AND expires_at>:now
        """), values)
        if consumed.rowcount != 1:
            return None
        intent_id = "synthetic-intent-" + secrets.token_hex(16)
        idempotency_key = hmac.new(
            auth.SECRET_KEY.encode(), ("payment-intent:" + hashed_proof).encode(),
            hashlib.sha256,
        ).hexdigest()
        db.execute(text("""
            INSERT INTO payment_authorized_intents_test
                (intent_id,user_id,session_hash,proof_hash,action_digest,
                 action_json,idempotency_key,status,created_at)
            VALUES (:intent,:user_id,:session_hash,:proof,:action,
                    :snapshot,:idempotency,'PENDING',:now)
        """), {**values, "intent": intent_id, "snapshot": canonical, "idempotency": idempotency_key})
        db.execute(AuditEvent.__table__.insert().values(
            user_id=claims["sub"], action="PAYMENT_INTENT_AUTHORIZED", category="SECURITY",
            resource_type="PAYMENT_INTENT", resource_id=intent_id, result="SUCCESS",
            reason="Synthetic authorized intent; not dispatched.", created_at=when,
        ))
    return {"intent_id": intent_id, "idempotency_key": idempotency_key, "status": "PENDING"}
