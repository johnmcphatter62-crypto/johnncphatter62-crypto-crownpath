"""Synthetic payment operation idempotency reservation (no provider calls).

The idempotency key is scoped to Owner, action and destination. A repeated
request returns its existing reservation; a conflicting reuse is rejected.
This does not implement production payment mutation or provider reconciliation.
"""
import sqlalchemy as sa
from sqlalchemy.orm import Session


def create_idempotency_test_schema(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS payment_operations_test (
                idempotency_key TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                destination TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING'
            )
        """))


def reserve_payment_operation_test(engine, *, idempotency_key, user_id,
                                   action, destination):
    values = (idempotency_key, user_id, action, destination)
    if not all(isinstance(v, str) and v.strip() for v in values):
        return "DENIED"
    with Session(engine) as db:
        with db.begin():
            result = db.execute(sa.text("""
                INSERT INTO payment_operations_test
                    (idempotency_key, user_id, action, destination)
                VALUES (:idempotency_key, :user_id, :action, :destination)
                ON CONFLICT(idempotency_key) DO NOTHING
            """), dict(zip(("idempotency_key", "user_id", "action",
                             "destination"), values)))
            if result.rowcount == 1:
                return "RESERVED"
            existing = db.execute(sa.text("""
                SELECT user_id, action, destination
                FROM payment_operations_test
                WHERE idempotency_key = :key
            """), {"key": idempotency_key}).one_or_none()
            if existing is not None and tuple(existing) == values[1:]:
                return "EXISTING"
            return "CONFLICT"
