"""Synthetic action-binding fixture, NOT a production authorization service.

Caller identities, session-active and CSRF assertions are test inputs. Real
signed-session verification, fresh action-specific MFA and provider operations
remain separate release gates. No live routes or migrations use this table.
"""
import hashlib
import hmac
import json
import re
import secrets

from sqlalchemy import text

from crownpath.payment_access import can_configure_payments


def action_digest(action):
    if not isinstance(action, dict) or set(action) != {
        "action", "provider_ref", "destination_ref", "currency",
    }:
        raise ValueError("Exact action fields required")
    if action["action"] != "payments.configure":
        raise ValueError("Unsupported purpose")
    for field in ("provider_ref", "destination_ref"):
        value = action[field]
        if not isinstance(value, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", value):
            raise ValueError("Synthetic identifier required")
    if not isinstance(action["currency"], str) or not re.fullmatch(r"[A-Z]{3}", action["currency"]):
        raise ValueError("Currency code required")
    canonical = json.dumps(action, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()


def _proof_hash(token, key):
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("Explicit synthetic key of at least 32 bytes required")
    return hmac.new(key, ("payment-action-proof:" + token).encode(), hashlib.sha256).hexdigest()


def create_action_binding_test_schema(engine):
    with engine.begin() as db:
        db.execute(text("""
            CREATE TABLE payment_action_bound_proofs_test (
                proof_hash VARCHAR(64) PRIMARY KEY,
                user_id VARCHAR(128) NOT NULL,
                session_id VARCHAR(128) NOT NULL,
                action_digest VARCHAR(64) NOT NULL,
                expires_at BIGINT NOT NULL,
                used_at BIGINT
            )
        """))


def issue_for_verified_fixture(engine, *, user_id, session_id, action, key, now, ttl=120):
    """Fixture issuer only; this function does NOT verify MFA."""
    if not all(isinstance(x, str) and x.strip() for x in (user_id, session_id)):
        raise ValueError("Synthetic actor/session required")
    if type(now) is not int or type(ttl) is not int or not 0 < ttl <= 120:
        raise ValueError("Bounded fixture time required")
    digest = action_digest(action)
    token = secrets.token_urlsafe(32)
    with engine.begin() as db:
        db.execute(text("""
            INSERT INTO payment_action_bound_proofs_test
                (proof_hash, user_id, session_id, action_digest, expires_at, used_at)
            VALUES (:proof, :user_id, :session_id, :action, :expiry, NULL)
        """), {"proof": _proof_hash(token, key), "user_id": user_id,
               "session_id": session_id, "action": digest, "expiry": now + ttl})
    return token


def consume_for_verified_fixture(
    engine, *, user, session_id, token, action, key, now,
    csrf_verified=False, session_active=False,
):
    """Atomic payload binding after synthetic trusted-policy preconditions."""
    if not (
        isinstance(user, dict)
        and isinstance(user.get("user_id"), str) and user["user_id"].strip()
        and can_configure_payments(user, recent_mfa_verified=True)
        and isinstance(session_id, str) and session_id.strip()
        and isinstance(token, str) and token
        and type(now) is int
        and csrf_verified is True and session_active is True
    ):
        return False
    try:
        digest = action_digest(action)
    except ValueError:
        return False
    with engine.begin() as db:
        result = db.execute(text("""
            UPDATE payment_action_bound_proofs_test SET used_at = :now
            WHERE proof_hash = :proof AND user_id = :user_id
              AND session_id = :session_id AND action_digest = :action
              AND used_at IS NULL AND expires_at > :now
        """), {"now": now, "proof": _proof_hash(token, key),
               "user_id": user["user_id"], "session_id": session_id, "action": digest})
        return result.rowcount == 1
