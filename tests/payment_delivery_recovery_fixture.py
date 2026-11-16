"""Fake-provider delivery/reconciliation fixture, never a production worker.

Fake calls occur under disposable database locks to exercise ordering. This is
not an approved production outbox/lease or network-transaction policy. Remote
idempotency and persistence are assumptions simulated by the fake provider.
"""
import json
import secrets
from datetime import datetime, timezone
from threading import Lock

from sqlalchemy import select, text

from crownpath.models import AuditEvent, AuthToken, User
from crownpath.permissions import has_permission
from tests.payment_action_binding_fixture import action_digest
from tests.payment_real_stepup_fixture import _begin_sqlite_write


class IdempotentFakeProvider:
    def __init__(self):
        self.changes = []
        self.calls = []
        self.accepted = {}
        self.fail_before_accept_once = False
        self.lose_response_once = False
        self._lock = Lock()

    def configure(self, key, action):
        snapshot = json.loads(json.dumps(action, sort_keys=True))
        with self._lock:
            self.calls.append(key)
            if self.fail_before_accept_once:
                self.fail_before_accept_once = False
                raise TimeoutError("synthetic timeout before acceptance")
            prior = self.accepted.get(key)
            if prior is not None:
                if prior["action"] != snapshot:
                    raise ValueError("Synthetic idempotency payload conflict")
                return prior["result"]
            result = "fake-result-" + secrets.token_hex(16)
            self.accepted[key] = {"action": snapshot, "result": result}
            self.changes.append(snapshot)
            if self.lose_response_once:
                self.lose_response_once = False
                raise TimeoutError("synthetic response lost after acceptance")
            return result


def create_delivery_test_schema(engine):
    with engine.begin() as db:
        db.execute(text("""
            CREATE TABLE payment_delivery_receipts_test (
                intent_id VARCHAR(64) PRIMARY KEY,
                provider_result VARCHAR(128) NOT NULL,
                created_at BIGINT NOT NULL,
                FOREIGN KEY (intent_id) REFERENCES payment_authorized_intents_test(intent_id)
            )
        """))


def dispatch_to_fake_provider(engine, *, intent_id, provider):
    if not isinstance(intent_id, str) or not intent_id:
        return None
    with engine.connect() as db:
        scope = db.execute(text("""
            SELECT user_id,session_hash FROM payment_authorized_intents_test WHERE intent_id=:intent
        """), {"intent": intent_id}).mappings().one_or_none()
    if scope is None:
        return None
    when = datetime.now(timezone.utc)
    with engine.begin() as db:
        _begin_sqlite_write(db)
        owner = db.execute(select(User.user_id, User.role, User.active, User.mfa_enabled).where(
            User.user_id == scope["user_id"], User.role == "OWNER",
            User.active.is_(True), User.mfa_enabled.is_(True),
        ).with_for_update()).mappings().one_or_none()
        if owner is None or not has_permission(owner, "payments.configure"):
            return None
        session = db.execute(select(AuthToken.token_id).where(
            AuthToken.user_id == scope["user_id"], AuthToken.token_hash == scope["session_hash"],
            AuthToken.token_type == "SESSION", AuthToken.used_at.is_(None),
            AuthToken.expires_at > when,
        ).with_for_update()).scalar_one_or_none()
        if session is None:
            return None
        intent = db.execute(text("""
            SELECT * FROM payment_authorized_intents_test
            WHERE intent_id=:intent AND user_id=:user_id AND session_hash=:session_hash
        """) if db.dialect.name != "postgresql" else text("""
            SELECT * FROM payment_authorized_intents_test
            WHERE intent_id=:intent AND user_id=:user_id AND session_hash=:session_hash FOR UPDATE
        """), {"intent": intent_id, **scope}).mappings().one_or_none()
        if intent is None:
            return None
        if intent["status"] == "DELIVERED":
            saved = db.scalar(text("""
                SELECT provider_result FROM payment_delivery_receipts_test WHERE intent_id=:intent
            """), {"intent": intent_id})
            if saved is None:
                raise RuntimeError("Synthetic delivered intent missing receipt")
            return {"intent_id": intent_id, "provider_result": saved, "status": "DELIVERED"}
        if intent["status"] != "PENDING":
            return None
        try:
            snapshot = json.loads(intent["action_json"])
            if action_digest(snapshot) != intent["action_digest"]:
                return None
        except (ValueError, TypeError):
            return None
        # A provider effect cannot be rolled back by a later local DB failure.
        # Stable remote idempotency is what permits safe reconciliation retries.
        result = provider.configure(intent["idempotency_key"], snapshot)
        db.execute(text("""
            INSERT INTO payment_delivery_receipts_test (intent_id,provider_result,created_at)
            VALUES (:intent,:result,:now)
        """), {"intent": intent_id, "result": result, "now": int(when.timestamp())})
        db.execute(text("""
            UPDATE payment_authorized_intents_test SET status='DELIVERED' WHERE intent_id=:intent
        """), {"intent": intent_id})
        db.execute(AuditEvent.__table__.insert().values(
            user_id=scope["user_id"], action="PAYMENT_INTENT_DELIVERED", category="SECURITY",
            resource_type="PAYMENT_INTENT", resource_id=intent_id, result="SUCCESS",
            reason="Synthetic fake-provider delivery completed.", created_at=when,
        ))
    return {"intent_id": intent_id, "provider_result": result, "status": "DELIVERED"}
