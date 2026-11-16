"""Fake-provider recovery only; no live provider or network operations."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

import pytest
import sqlalchemy as sa

from crownpath import auth
from crownpath.models import AuditEvent, User
from tests.payment_delivery_recovery_fixture import (
    IdempotentFakeProvider, create_delivery_test_schema, dispatch_to_fake_provider,
)
from tests.test_payment_durable_intent_audit import intent_flow, authorize
from tests.test_payment_real_stepup_binding import real_stepup
from tests.test_payment_action_payload_binding import ACTION


@pytest.fixture
def delivery_flow(intent_flow):
    receipt = authorize(intent_flow)
    assert receipt
    create_delivery_test_schema(intent_flow[0][0])
    return intent_flow, receipt, IdempotentFakeProvider()


def dispatch(fixture):
    flow, receipt, provider = fixture
    return dispatch_to_fake_provider(
        flow[0][0], intent_id=receipt["intent_id"], provider=provider,
    )


def delivery_state(fixture):
    flow, receipt, provider = fixture
    with flow[0][0].connect() as db:
        return (
            db.scalar(sa.text("SELECT status FROM payment_authorized_intents_test")),
            db.scalar(sa.text("SELECT count(*) FROM payment_delivery_receipts_test")),
            db.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(
                AuditEvent.action == "PAYMENT_INTENT_DELIVERED",
            )),
        )


def test_successful_delivery_and_retry_make_one_provider_change(delivery_flow):
    first = dispatch(delivery_flow)
    assert first and first["status"] == "DELIVERED"
    assert dispatch(delivery_flow) == first
    assert delivery_flow[2].changes == [ACTION]
    assert len(delivery_flow[2].calls) == 1
    assert delivery_state(delivery_flow) == ("DELIVERED", 1, 1)


def test_timeout_before_provider_acceptance_can_retry(delivery_flow):
    provider = delivery_flow[2]
    provider.fail_before_accept_once = True
    with pytest.raises(TimeoutError, match="before acceptance"):
        dispatch(delivery_flow)
    assert provider.changes == []
    assert delivery_state(delivery_flow) == ("PENDING", 0, 0)
    assert dispatch(delivery_flow)
    assert provider.changes == [ACTION]
    assert len(set(provider.calls)) == 1
    assert delivery_state(delivery_flow) == ("DELIVERED", 1, 1)


def test_lost_response_reconciles_without_duplicate_provider_effect(delivery_flow):
    provider = delivery_flow[2]
    provider.lose_response_once = True
    with pytest.raises(TimeoutError, match="lost after acceptance"):
        dispatch(delivery_flow)
    assert provider.changes == [ACTION]
    assert delivery_state(delivery_flow) == ("PENDING", 0, 0)
    saved_result = next(iter(provider.accepted.values()))["result"]
    recovered = dispatch(delivery_flow)
    assert recovered["provider_result"] == saved_result
    assert provider.changes == [ACTION]
    assert len(provider.calls) == 2 and len(set(provider.calls)) == 1
    assert delivery_state(delivery_flow) == ("DELIVERED", 1, 1)


@pytest.mark.parametrize("failed_table", ["PAYMENT_DELIVERY_RECEIPTS_TEST", "AUDIT_EVENTS"])
def test_local_write_failure_reconciles_accepted_provider_effect(delivery_flow, failed_table):
    engine = delivery_flow[0][0][0]
    provider = delivery_flow[2]

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO " + failed_table):
            raise RuntimeError("synthetic delivery persistence failure")

    sa.event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic delivery persistence failure"):
            dispatch(delivery_flow)
    finally:
        sa.event.remove(engine, "before_cursor_execute", fail_insert)
    assert provider.changes == [ACTION]
    assert delivery_state(delivery_flow) == ("PENDING", 0, 0)
    assert dispatch(delivery_flow)
    assert provider.changes == [ACTION]
    assert len(set(provider.calls)) == 1
    assert delivery_state(delivery_flow) == ("DELIVERED", 1, 1)


def test_competing_workers_create_one_delivery_record(delivery_flow):
    start = Barrier(2)

    def attempt():
        start.wait(timeout=10)
        return dispatch(delivery_flow)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt)
        b = pool.submit(attempt)
        receipts = [a.result(timeout=20), b.result(timeout=20)]
    assert receipts[0] and receipts[0] == receipts[1]
    assert delivery_flow[2].changes == [ACTION]
    assert len(delivery_flow[2].calls) == 1
    assert delivery_state(delivery_flow) == ("DELIVERED", 1, 1)


@pytest.mark.parametrize("change", ["logout", "inactive", "role", "mfa"])
def test_revocation_before_dispatch_denies_provider_call(delivery_flow, change):
    flow, receipt, provider = delivery_flow
    engine, cookie = flow[0][0], flow[0][1]
    if change == "logout":
        assert auth.revoke_access_token(cookie)
    else:
        values = {"active": False} if change == "inactive" else (
            {"role": "BARBER"} if change == "role" else {"mfa_enabled": False}
        )
        with engine.begin() as db:
            db.execute(sa.update(User).where(User.user_id == "stepup-owner").values(**values))
    assert dispatch(delivery_flow) is None
    assert provider.calls == [] and provider.changes == []
    assert delivery_state(delivery_flow) == ("PENDING", 0, 0)


def test_corrupted_stored_payload_cannot_reach_provider(delivery_flow):
    engine = delivery_flow[0][0][0]
    with engine.begin() as db:
        db.execute(sa.text(
            "UPDATE payment_authorized_intents_test SET action_json=:changed"
        ), {"changed": json.dumps({**ACTION, "destination_ref": "synthetic-destination-b"})})
    assert dispatch(delivery_flow) is None
    assert delivery_flow[2].calls == []
    assert delivery_state(delivery_flow) == ("PENDING", 0, 0)


def test_missing_receipt_cannot_trigger_a_second_provider_call(delivery_flow):
    assert dispatch(delivery_flow)
    with delivery_flow[0][0][0].begin() as db:
        db.execute(sa.text("DELETE FROM payment_delivery_receipts_test"))
    with pytest.raises(RuntimeError, match="missing receipt"):
        dispatch(delivery_flow)
    assert delivery_flow[2].changes == [ACTION]
    assert len(delivery_flow[2].calls) == 1
