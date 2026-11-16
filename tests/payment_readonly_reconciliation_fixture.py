"""Read-only fake-provider lookup for recording an already-accepted effect.

Trusted internal test worker only: no operator/HTTP access-control model,
production provider auth, live network, or approved lease/outbox policy.
This never calls configure and never restores a revoked user/session.
"""
import json
from copy import deepcopy
from datetime import datetime, timezone

from sqlalchemy import select, text

from crownpath.models import AuditEvent
from tests.payment_action_binding_fixture import action_digest
from tests.payment_delivery_recovery_fixture import IdempotentFakeProvider
from tests.payment_real_stepup_fixture import _begin_sqlite_write


class LookupFakeProvider(IdempotentFakeProvider):
    def __init__(self):
        super().__init__()
        self.lookups = []

    def lookup(self, key):
        with self._lock:
            self.lookups.append(key)
            return deepcopy(self.accepted.get(key))


def reconcile_accepted_effect(engine, *, intent_id, provider):
    if not isinstance(intent_id, str) or not intent_id:
        return None
    when = datetime.now(timezone.utc)
    with engine.begin() as db:
        _begin_sqlite_write(db)
        query = "SELECT * FROM payment_authorized_intents_test WHERE intent_id=:intent"
        if db.dialect.name == "postgresql":
            query += " FOR UPDATE"
        intent = db.execute(text(query), {"intent": intent_id}).mappings().one_or_none()
        if intent is None or intent["status"] not in ("PENDING", "DELIVERED"):
            return None
        try:
            approved = json.loads(intent["action_json"])
            if action_digest(approved) != intent["action_digest"]:
                return None
        except (TypeError, ValueError):
            return None
        saved = db.scalar(text(
            "SELECT provider_result FROM payment_delivery_receipts_test WHERE intent_id=:intent"
        ), {"intent": intent_id})
        if intent["status"] == "DELIVERED" and saved is not None:
            return {"intent_id": intent_id, "provider_result": saved, "status": "DELIVERED"}

        accepted = provider.lookup(intent["idempotency_key"])
        if accepted is None:
            return None
        if (
            not isinstance(accepted, dict)
            or not isinstance(accepted.get("result"), str) or not accepted["result"]
            or action_digest(accepted.get("action")) != intent["action_digest"]
        ):
            raise ValueError("Synthetic provider lookup does not match approved action")
        result = accepted["result"]
        if saved is not None and saved != result:
            raise ValueError("Synthetic stored receipt conflicts with provider lookup")
        if saved is None:
            db.execute(text("""
                INSERT INTO payment_delivery_receipts_test (intent_id,provider_result,created_at)
                VALUES (:intent,:result,:now)
            """), {"intent": intent_id, "result": result, "now": int(when.timestamp())})
        db.execute(text(
            "UPDATE payment_authorized_intents_test SET status='DELIVERED' WHERE intent_id=:intent"
        ), {"intent": intent_id})
        already_audited = db.scalar(select(AuditEvent.audit_id).where(
            AuditEvent.action == "PAYMENT_INTENT_DELIVERED",
            AuditEvent.resource_id == intent_id, AuditEvent.result == "SUCCESS",
        ).limit(1))
        if already_audited is None:
            db.execute(AuditEvent.__table__.insert().values(
                user_id=intent["user_id"], action="PAYMENT_INTENT_DELIVERED", category="SECURITY",
                resource_type="PAYMENT_INTENT", resource_id=intent_id, result="SUCCESS",
                reason="Read-only synthetic reconciliation of prior acceptance; no new provider change.",
                created_at=when,
            ))
    return {"intent_id": intent_id, "provider_result": result, "status": "DELIVERED"}
