"""One-use challenge acceptance on a guarded disposable PostgreSQL schema."""
import pytest
import sqlalchemy as sa

from tests import test_payment_one_use_action_challenge as checks
from tests.payment_one_use_challenge_fixture import create_action_challenge_test_schema
from tests.test_payment_real_stepup_postgres import real_stepup_postgres
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine
from tests.test_payment_real_stepup_binding import apply
from tests.test_payment_action_payload_binding import ACTION


@pytest.fixture
def one_use_postgres(real_stepup_postgres):
    create_action_challenge_test_schema(real_stepup_postgres[0])
    return real_stepup_postgres


def test_postgres_challenge_issues_one_proof_and_denies_replay(one_use_postgres):
    checks.test_challenge_issues_one_proof_and_replay_cannot_issue_another(one_use_postgres)


@pytest.mark.parametrize("change", [
    {"destination_ref": "synthetic-destination-b"},
    {"provider_ref": "fake-provider-b"}, {"currency": "EUR"}, {"action": "profile.edit"},
])
def test_postgres_changed_action_does_not_burn_challenge(one_use_postgres, change):
    checks.test_changed_action_cannot_verify_or_burn_challenge(one_use_postgres, change)


def test_postgres_other_session_cannot_claim(one_use_postgres):
    checks.test_other_session_cannot_claim_challenge(one_use_postgres)


def test_postgres_expired_challenge_denies(one_use_postgres):
    checks.test_expired_challenge_cannot_issue_proof(one_use_postgres)


def test_postgres_failed_codes_close_challenge_and_lock_account(one_use_postgres):
    checks.test_five_bad_codes_close_challenge_and_enforce_real_account_lockout(one_use_postgres)


def test_postgres_injected_proof_failure_rolls_back_challenge(one_use_postgres):
    checks.test_proof_write_failure_rolls_back_challenge_claim(one_use_postgres)


def test_postgres_competing_confirmations_issue_one_proof(one_use_postgres):
    checks.test_two_confirmations_create_one_proof(one_use_postgres)


def test_postgres_logout_prevents_confirmation(one_use_postgres):
    checks.test_logout_prevents_challenge_confirmation(one_use_postgres)


def test_postgres_real_constraint_failure_preserves_challenge_for_retry(one_use_postgres):
    engine = one_use_postgres[0]
    challenge = checks.create(one_use_postgres)
    assert challenge
    with engine.begin() as db:
        db.execute(sa.text(
            "ALTER TABLE payment_action_bound_proofs_test "
            "ADD CONSTRAINT reject_new_proof CHECK (used_at IS NOT NULL)"
        ))
    try:
        with pytest.raises(sa.exc.IntegrityError) as error:
            checks.confirm(one_use_postgres, challenge)
        assert error.value.orig.sqlstate == "23514"
        with engine.connect() as db:
            assert db.scalar(sa.text(
                "SELECT consumed_at FROM payment_action_challenges_test"
            )) is None
        assert checks.proof_count(one_use_postgres) == 0
        assert one_use_postgres[3].changes == []
    finally:
        with engine.begin() as db:
            db.execute(sa.text(
                "ALTER TABLE payment_action_bound_proofs_test DROP CONSTRAINT reject_new_proof"
            ))
    proof = checks.confirm(one_use_postgres, challenge)
    assert proof
    assert checks.confirm(one_use_postgres, challenge) is None
    assert checks.proof_count(one_use_postgres) == 1
    assert apply(one_use_postgres, proof)
    assert not apply(one_use_postgres, proof)
    assert one_use_postgres[3].changes == [ACTION]
