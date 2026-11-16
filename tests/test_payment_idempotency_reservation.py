"""Disposable SQLite idempotency acceptance tests; no payment provider."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
import sqlalchemy as sa

from crownpath.payment_idempotency_test_adapter import (
    create_idempotency_test_schema,
    reserve_payment_operation_test,
)

BASE = dict(idempotency_key="synthetic-key", user_id="owner-a",
            action="payments.configure", destination="synthetic-destination")


@pytest.fixture
def engine(tmp_path):
    db = sa.create_engine(f"sqlite:///{tmp_path / 'idempotency.db'}",
                          connect_args={"timeout": 20})
    create_idempotency_test_schema(db)
    yield db
    db.dispose()


def reserve(engine, **changes):
    values = dict(BASE)
    values.update(changes)
    return reserve_payment_operation_test(engine, **values)


def test_matching_retry_returns_existing_without_duplicate(engine):
    assert reserve(engine) == "RESERVED"
    assert reserve(engine) == "EXISTING"
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT count(*) FROM payment_operations_test")) == 1


@pytest.mark.parametrize("change", [
    {"user_id": "owner-b"}, {"action": "payments.refund"},
    {"destination": "different-destination"},
])
def test_conflicting_reuse_is_denied(engine, change):
    assert reserve(engine) == "RESERVED"
    assert reserve(engine, **change) == "CONFLICT"
    assert reserve(engine) == "EXISTING"


def test_missing_key_or_identity_denied(engine):
    assert reserve(engine, idempotency_key="") == "DENIED"
    assert reserve(engine, user_id="") == "DENIED"


def test_concurrent_matching_requests_create_one_reservation(engine):
    barrier = Barrier(2)

    def worker():
        barrier.wait(timeout=15)
        return reserve(engine)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker)
        second = pool.submit(worker)
        outcomes = [first.result(timeout=25), second.result(timeout=25)]
    assert sorted(outcomes) == ["EXISTING", "RESERVED"]
    with engine.connect() as conn:
        assert conn.scalar(sa.text("SELECT count(*) FROM payment_operations_test")) == 1
