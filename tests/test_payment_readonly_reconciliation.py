"""Read-only provider evidence recovery after revocation; no live provider."""
from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier

import pytest
import sqlalchemy as sa

from crownpath import auth
from crownpath.models import User
from tests.payment_readonly_reconciliation_fixture import LookupFakeProvider, reconcile_accepted_effect
from tests import test_payment_delivery_recovery as checks
from tests.test_payment_delivery_recovery import delivery_flow
from tests.test_payment_durable_intent_audit import intent_flow, authorize
from tests.test_payment_real_stepup_binding import real_stepup
from tests.test_payment_action_payload_binding import ACTION


@pytest.fixture
def reconciliation_flow(delivery_flow):
    return delivery_flow[0], delivery_flow[1], LookupFakeProvider()


def reconcile(fixture):
    return reconcile_accepted_effect(
        fixture[0][0][0], intent_id=fixture[1]["intent_id"], provider=fixture[2],
    )


def lost_acceptance(fixture):
    fixture[2].lose_response_once = True
    with pytest.raises(TimeoutError, match="lost after acceptance"):
        checks.dispatch(fixture)
    assert fixture[2].changes == [ACTION]
    assert checks.delivery_state(fixture) == ("PENDING", 0, 0)


def test_logout_allows_only_readonly_reconciliation_of_prior_acceptance(reconciliation_flow):
    flow = reconciliation_flow
    lost_acceptance(flow)
    assert auth.revoke_access_token(flow[0][0][1])
    assert checks.dispatch(flow) is None
    result = reconcile(flow)
    assert result and result["status"] == "DELIVERED"
    assert reconcile(flow) == result
    assert flow[2].changes == [ACTION]
    assert len(flow[2].calls) == 1 and len(flow[2].lookups) == 1
    assert checks.delivery_state(flow) == ("DELIVERED", 1, 1)
    assert auth.decode_access_token(flow[0][0][1]) is None
    assert authorize(flow[0]) is None


@pytest.mark.parametrize("change", [{"active": False}, {"role": "BARBER"}, {"mfa_enabled": False}])
def test_account_revocation_does_not_erase_prior_provider_evidence(reconciliation_flow, change):
    flow = reconciliation_flow
    lost_acceptance(flow)
    with flow[0][0][0].begin() as db:
        db.execute(sa.update(User).where(User.user_id == "stepup-owner").values(**change))
    assert checks.dispatch(flow) is None
    assert reconcile(flow)
    assert checks.delivery_state(flow) == ("DELIVERED", 1, 1)
    assert flow[2].changes == [ACTION] and len(flow[2].calls) == 1
    user = auth.get_user_by_id("stepup-owner")
    for name, value in change.items():
        assert user[name] == value
    assert authorize(flow[0]) is None


def test_absent_acceptance_after_logout_does_not_submit_any_change(reconciliation_flow):
    flow = reconciliation_flow
    flow[2].fail_before_accept_once = True
    with pytest.raises(TimeoutError, match="before acceptance"):
        checks.dispatch(flow)
    assert auth.revoke_access_token(flow[0][0][1])
    assert reconcile(flow) is None
    assert flow[2].changes == [] and len(flow[2].calls) == 1
    assert checks.delivery_state(flow) == ("PENDING", 0, 0)


@pytest.mark.parametrize("failed_table", ["PAYMENT_DELIVERY_RECEIPTS_TEST", "AUDIT_EVENTS"])
def test_reconciliation_write_failure_can_retry_without_resubmission(reconciliation_flow, failed_table):
    flow = reconciliation_flow
    lost_acceptance(flow)
    assert auth.revoke_access_token(flow[0][0][1])
    engine = flow[0][0][0]

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO " + failed_table):
            raise RuntimeError("synthetic read-only reconciliation persistence failure")

    sa.event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic read-only reconciliation"):
            reconcile(flow)
    finally:
        sa.event.remove(engine, "before_cursor_execute", fail_insert)
    assert checks.delivery_state(flow) == ("PENDING", 0, 0)
    assert len(flow[2].calls) == 1
    assert reconcile(flow)
    assert checks.delivery_state(flow) == ("DELIVERED", 1, 1)
    assert len(flow[2].calls) == 1 and len(flow[2].lookups) == 2
    assert flow[2].changes == [ACTION]


def test_missing_receipt_is_repaired_without_duplicate_delivery_audit(reconciliation_flow):
    flow = reconciliation_flow
    first = checks.dispatch(flow)
    assert first
    with flow[0][0][0].begin() as db:
        db.execute(sa.text("DELETE FROM payment_delivery_receipts_test"))
    assert reconcile(flow) == first
    assert checks.delivery_state(flow) == ("DELIVERED", 1, 1)
    assert flow[2].changes == [ACTION]
    assert len(flow[2].calls) == 1 and len(flow[2].lookups) == 1


def test_mismatched_provider_lookup_cannot_mark_intent_delivered(reconciliation_flow):
    flow = reconciliation_flow
    lost_acceptance(flow)
    key = next(iter(flow[2].accepted))
    flow[2].accepted[key] = {
        **flow[2].accepted[key],
        "action": {**ACTION, "destination_ref": "synthetic-destination-b"},
    }
    with pytest.raises(ValueError, match="does not match approved action"):
        reconcile(flow)
    assert checks.delivery_state(flow) == ("PENDING", 0, 0)
    assert flow[2].changes == [ACTION] and len(flow[2].calls) == 1


def test_corrupted_local_action_blocks_lookup_and_recording(reconciliation_flow):
    flow = reconciliation_flow
    lost_acceptance(flow)
    with flow[0][0][0].begin() as db:
        db.execute(sa.text(
            "UPDATE payment_authorized_intents_test SET action_json=:changed"
        ), {"changed": json.dumps({**ACTION, "currency": "EUR"})})
    assert reconcile(flow) is None
    assert flow[2].lookups == []
    assert checks.delivery_state(flow) == ("PENDING", 0, 0)


def test_two_reconcilers_write_one_receipt_and_audit(reconciliation_flow):
    flow = reconciliation_flow
    lost_acceptance(flow)
    assert auth.revoke_access_token(flow[0][0][1])
    start = Barrier(2)

    def attempt():
        start.wait(timeout=10)
        return reconcile(flow)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt)
        b = pool.submit(attempt)
        results = [a.result(timeout=20), b.result(timeout=20)]
    assert results[0] and results[0] == results[1]
    assert checks.delivery_state(flow) == ("DELIVERED", 1, 1)
    assert flow[2].changes == [ACTION]
    assert len(flow[2].calls) == 1 and len(flow[2].lookups) == 1
