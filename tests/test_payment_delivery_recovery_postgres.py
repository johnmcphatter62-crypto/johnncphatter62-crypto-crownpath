"""Fake-provider delivery recovery on guarded disposable PostgreSQL."""
import pytest
import sqlalchemy as sa

from tests import test_payment_delivery_recovery as checks
from tests.payment_delivery_recovery_fixture import IdempotentFakeProvider, create_delivery_test_schema
from tests.test_payment_durable_intent_postgres import postgres_intent_flow
from tests.test_payment_real_stepup_postgres import real_stepup_postgres
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine
from tests.test_payment_action_payload_binding import ACTION


@pytest.fixture
def postgres_delivery_flow(postgres_intent_flow):
    receipt = checks.authorize(postgres_intent_flow)
    assert receipt
    create_delivery_test_schema(postgres_intent_flow[0][0])
    return postgres_intent_flow, receipt, IdempotentFakeProvider()


def test_postgres_successful_delivery_replay(postgres_delivery_flow):
    checks.test_successful_delivery_and_retry_make_one_provider_change(postgres_delivery_flow)


def test_postgres_timeout_before_acceptance(postgres_delivery_flow):
    checks.test_timeout_before_provider_acceptance_can_retry(postgres_delivery_flow)


def test_postgres_lost_provider_response_reconciles(postgres_delivery_flow):
    checks.test_lost_response_reconciles_without_duplicate_provider_effect(postgres_delivery_flow)


@pytest.mark.parametrize("failed_table", ["PAYMENT_DELIVERY_RECEIPTS_TEST", "AUDIT_EVENTS"])
def test_postgres_injected_local_failure_reconciles(postgres_delivery_flow, failed_table):
    checks.test_local_write_failure_reconciles_accepted_provider_effect(postgres_delivery_flow, failed_table)


def test_postgres_competing_workers_have_one_delivery(postgres_delivery_flow):
    checks.test_competing_workers_create_one_delivery_record(postgres_delivery_flow)


@pytest.mark.parametrize("change", ["logout", "inactive", "role", "mfa"])
def test_postgres_revoked_scope_blocks_dispatch(postgres_delivery_flow, change):
    checks.test_revocation_before_dispatch_denies_provider_call(postgres_delivery_flow, change)


def test_postgres_corrupted_payload_blocks_dispatch(postgres_delivery_flow):
    checks.test_corrupted_stored_payload_cannot_reach_provider(postgres_delivery_flow)


def test_postgres_missing_receipt_does_not_duplicate_provider_call(postgres_delivery_flow):
    checks.test_missing_receipt_cannot_trigger_a_second_provider_call(postgres_delivery_flow)


@pytest.mark.parametrize("failed_table", ["payment_delivery_receipts_test", "audit_events"])
def test_postgres_real_constraint_failure_reconciles_accepted_effect(postgres_delivery_flow, failed_table):
    engine = postgres_delivery_flow[0][0][0]
    provider = postgres_delivery_flow[2]
    expression = (
        "provider_result = 'reject-all-synthetic-results'"
        if failed_table == "payment_delivery_receipts_test"
        else "action <> 'PAYMENT_INTENT_DELIVERED'"
    )
    # Only fixed test identifiers/expressions are interpolated.
    with engine.begin() as db:
        db.execute(sa.text(
            f"ALTER TABLE {failed_table} ADD CONSTRAINT reject_delivery_record CHECK ({expression})"
        ))
    try:
        with pytest.raises(sa.exc.IntegrityError) as error:
            checks.dispatch(postgres_delivery_flow)
        assert error.value.orig.sqlstate == "23514"
        # Remote acceptance survives local rollback and needs reconciliation.
        assert provider.changes == [ACTION]
        assert checks.delivery_state(postgres_delivery_flow) == ("PENDING", 0, 0)
        accepted = next(iter(provider.accepted.values()))["result"]
    finally:
        with engine.begin() as db:
            db.execute(sa.text(
                f"ALTER TABLE {failed_table} DROP CONSTRAINT reject_delivery_record"
            ))
    recovered = checks.dispatch(postgres_delivery_flow)
    assert recovered["provider_result"] == accepted
    assert provider.changes == [ACTION]
    assert len(provider.calls) == 2 and len(set(provider.calls)) == 1
    assert checks.delivery_state(postgres_delivery_flow) == ("DELIVERED", 1, 1)
