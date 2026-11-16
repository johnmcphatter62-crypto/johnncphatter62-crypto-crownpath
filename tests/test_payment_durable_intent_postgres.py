"""Intent/proof/audit atomicity on a guarded disposable PostgreSQL schema."""
import pyotp
import pytest
import sqlalchemy as sa

from tests import test_payment_durable_intent_audit as checks
from tests.payment_intent_audit_fixture import create_intent_audit_test_schema
from tests.payment_one_use_challenge_fixture import (
    create_action_challenge_test_schema, create_action_challenge, confirm_action_challenge,
)
from tests.payment_real_stepup_fixture import ORIGIN
from tests.test_payment_action_payload_binding import ACTION
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine
from tests.test_payment_real_stepup_postgres import real_stepup_postgres


@pytest.fixture
def postgres_intent_flow(real_stepup_postgres):
    engine, cookie, secret, provider = real_stepup_postgres
    create_action_challenge_test_schema(engine)
    create_intent_audit_test_schema(engine)
    challenge = create_action_challenge(engine, cookie=cookie, action=dict(ACTION), origin=ORIGIN)
    proof = confirm_action_challenge(
        engine, cookie=cookie, challenge=challenge, action=dict(ACTION),
        code=pyotp.TOTP(secret).now(), origin=ORIGIN,
    )
    assert proof
    return real_stepup_postgres, proof


def test_postgres_authorization_retry_has_one_intent_and_audit(postgres_intent_flow):
    checks.test_authorization_retry_returns_one_durable_intent_and_audit(postgres_intent_flow)


@pytest.mark.parametrize("failed_table", ["PAYMENT_AUTHORIZED_INTENTS_TEST", "AUDIT_EVENTS"])
def test_postgres_injected_write_failure_rolls_back_all_records(postgres_intent_flow, failed_table):
    checks.test_write_failure_rolls_back_proof_intent_and_audit(postgres_intent_flow, failed_table)


def test_postgres_changed_payload_denies_intent_receipt(postgres_intent_flow):
    checks.test_changed_payload_cannot_create_intent_or_retrieve_receipt(postgres_intent_flow)


def test_postgres_competing_requests_return_same_receipt(postgres_intent_flow):
    checks.test_competing_authorizations_return_same_receipt(postgres_intent_flow)


def test_postgres_logout_denies_receipt(postgres_intent_flow):
    checks.test_logout_denies_access_to_prior_intent_receipt(postgres_intent_flow)


def test_postgres_approved_snapshot_is_persisted(postgres_intent_flow):
    checks.test_intent_keeps_authorized_snapshot_after_original_changes(postgres_intent_flow)


def test_postgres_expired_proof_denies_intent(postgres_intent_flow):
    checks.test_expired_proof_cannot_create_durable_intent(postgres_intent_flow)


@pytest.mark.parametrize("failed_table", ["payment_authorized_intents_test", "audit_events"])
def test_postgres_real_constraint_failure_is_atomic(postgres_intent_flow, failed_table):
    engine = postgres_intent_flow[0][0]
    # Names and expressions are fixed test constants, never request inputs.
    expression = (
        "status <> 'PENDING'" if failed_table == "payment_authorized_intents_test"
        else "action <> 'PAYMENT_INTENT_AUTHORIZED'"
    )
    with engine.begin() as db:
        db.execute(sa.text(
            f"ALTER TABLE {failed_table} ADD CONSTRAINT reject_intent_flow CHECK ({expression})"
        ))
    try:
        with pytest.raises(sa.exc.IntegrityError) as error:
            checks.authorize(postgres_intent_flow)
        assert error.value.orig.sqlstate == "23514"
        assert checks.counts(postgres_intent_flow) == (0, 0)
        with engine.connect() as db:
            assert db.scalar(sa.text(
                "SELECT used_at FROM payment_action_bound_proofs_test"
            )) is None
        assert postgres_intent_flow[0][3].changes == []
    finally:
        with engine.begin() as db:
            db.execute(sa.text(
                f"ALTER TABLE {failed_table} DROP CONSTRAINT reject_intent_flow"
            ))
    receipt = checks.authorize(postgres_intent_flow)
    assert receipt
    assert checks.authorize(postgres_intent_flow) == receipt
    assert checks.counts(postgres_intent_flow) == (1, 1)
    assert postgres_intent_flow[0][3].changes == []
