"""Read-only fake-provider recovery on guarded disposable PostgreSQL."""
import pytest
import sqlalchemy as sa

from crownpath import auth
from tests import test_payment_readonly_reconciliation as checks
from tests.payment_readonly_reconciliation_fixture import LookupFakeProvider
from tests.test_payment_delivery_recovery_postgres import postgres_delivery_flow
from tests.test_payment_durable_intent_postgres import postgres_intent_flow
from tests.test_payment_real_stepup_postgres import real_stepup_postgres
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


@pytest.fixture
def postgres_reconciliation_flow(postgres_delivery_flow):
    return postgres_delivery_flow[0], postgres_delivery_flow[1], LookupFakeProvider()


def test_postgres_logout_preserves_only_historical_evidence(postgres_reconciliation_flow):
    checks.test_logout_allows_only_readonly_reconciliation_of_prior_acceptance(postgres_reconciliation_flow)


@pytest.mark.parametrize("change", [{"active": False}, {"role": "BARBER"}, {"mfa_enabled": False}])
def test_postgres_account_revocation_preserves_evidence(postgres_reconciliation_flow, change):
    checks.test_account_revocation_does_not_erase_prior_provider_evidence(postgres_reconciliation_flow, change)


def test_postgres_absent_acceptance_does_not_submit(postgres_reconciliation_flow):
    checks.test_absent_acceptance_after_logout_does_not_submit_any_change(postgres_reconciliation_flow)


@pytest.mark.parametrize("failed_table", ["PAYMENT_DELIVERY_RECEIPTS_TEST", "AUDIT_EVENTS"])
def test_postgres_injected_write_failure_can_retry(postgres_reconciliation_flow, failed_table):
    checks.test_reconciliation_write_failure_can_retry_without_resubmission(postgres_reconciliation_flow, failed_table)


def test_postgres_missing_receipt_repair(postgres_reconciliation_flow):
    checks.test_missing_receipt_is_repaired_without_duplicate_delivery_audit(postgres_reconciliation_flow)


def test_postgres_mismatched_provider_lookup_is_rejected(postgres_reconciliation_flow):
    checks.test_mismatched_provider_lookup_cannot_mark_intent_delivered(postgres_reconciliation_flow)


def test_postgres_corrupted_local_action_blocks_lookup(postgres_reconciliation_flow):
    checks.test_corrupted_local_action_blocks_lookup_and_recording(postgres_reconciliation_flow)


def test_postgres_competing_reconcilers_record_once(postgres_reconciliation_flow):
    checks.test_two_reconcilers_write_one_receipt_and_audit(postgres_reconciliation_flow)


@pytest.mark.parametrize("failed_table", ["payment_delivery_receipts_test", "audit_events"])
def test_postgres_constraint_failure_rolls_back_reconciliation(postgres_reconciliation_flow, failed_table):
    flow = postgres_reconciliation_flow
    checks.lost_acceptance(flow)
    assert auth.revoke_access_token(flow[0][0][1])
    engine = flow[0][0][0]
    expression = (
        "provider_result = 'reject-all-synthetic-results'"
        if failed_table == "payment_delivery_receipts_test"
        else "action <> 'PAYMENT_INTENT_DELIVERED'"
    )
    # Identifiers and expressions come only from the fixed parameters above.
    with engine.begin() as db:
        db.execute(sa.text(
            f"ALTER TABLE {failed_table} ADD CONSTRAINT reject_reconciliation CHECK ({expression})"
        ))
    try:
        with pytest.raises(sa.exc.IntegrityError) as error:
            checks.reconcile(flow)
        assert error.value.orig.sqlstate == "23514"
        assert checks.checks.delivery_state(flow) == ("PENDING", 0, 0)
        assert len(flow[2].calls) == 1
    finally:
        with engine.begin() as db:
            db.execute(sa.text(
                f"ALTER TABLE {failed_table} DROP CONSTRAINT reject_reconciliation"
            ))
    assert checks.reconcile(flow)
    assert checks.checks.delivery_state(flow) == ("DELIVERED", 1, 1)
    assert len(flow[2].changes) == 1 and len(flow[2].calls) == 1
    assert len(flow[2].lookups) == 2
    assert checks.checks.dispatch(flow) is None
