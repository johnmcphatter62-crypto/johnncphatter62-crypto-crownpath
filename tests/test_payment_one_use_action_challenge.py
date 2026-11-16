"""One-use challenge acceptance with real TOTP and disposable SQLite records."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pyotp
import pytest
import sqlalchemy as sa

from crownpath import auth
from tests.payment_one_use_challenge_fixture import (
    create_action_challenge_test_schema, create_action_challenge, confirm_action_challenge,
)
from tests.payment_real_stepup_fixture import ORIGIN
from tests.test_payment_real_stepup_binding import real_stepup, apply
from tests.test_payment_action_payload_binding import ACTION


@pytest.fixture
def challenge_flow(real_stepup):
    create_action_challenge_test_schema(real_stepup[0])
    return real_stepup


def create(fixture):
    return create_action_challenge(
        fixture[0], cookie=fixture[1], action=dict(ACTION), origin=ORIGIN,
    )


def confirm(fixture, challenge, **changes):
    values = dict(
        cookie=fixture[1], challenge=challenge, action=dict(ACTION),
        code=pyotp.TOTP(fixture[2]).now(), origin=ORIGIN,
    )
    values.update(changes)
    return confirm_action_challenge(fixture[0], **values)


def proof_count(fixture):
    with fixture[0].connect() as db:
        return db.scalar(sa.text("SELECT count(*) FROM payment_action_bound_proofs_test"))


def test_challenge_issues_one_proof_and_replay_cannot_issue_another(challenge_flow):
    challenge = create(challenge_flow)
    assert challenge
    proof = confirm(challenge_flow, challenge)
    assert proof
    assert confirm(challenge_flow, challenge) is None
    assert proof_count(challenge_flow) == 1
    assert apply(challenge_flow, proof)
    assert not apply(challenge_flow, proof)
    assert challenge_flow[3].changes == [ACTION]


@pytest.mark.parametrize("change", [
    {"destination_ref": "synthetic-destination-b"},
    {"provider_ref": "fake-provider-b"}, {"currency": "EUR"}, {"action": "profile.edit"},
])
def test_changed_action_cannot_verify_or_burn_challenge(challenge_flow, change):
    challenge = create(challenge_flow)
    assert challenge
    assert confirm(challenge_flow, challenge, action={**ACTION, **change}) is None
    assert proof_count(challenge_flow) == 0
    assert confirm(challenge_flow, challenge)
    assert proof_count(challenge_flow) == 1


def test_other_session_cannot_claim_challenge(challenge_flow):
    challenge = create(challenge_flow)
    other = auth.create_access_token("stepup-owner", mfa_verified=True)
    assert confirm(challenge_flow, challenge, cookie=other) is None
    assert confirm(challenge_flow, challenge)
    assert proof_count(challenge_flow) == 1


def test_expired_challenge_cannot_issue_proof(challenge_flow):
    challenge = create(challenge_flow)
    with challenge_flow[0].begin() as db:
        db.execute(sa.text(
            "UPDATE payment_action_challenges_test SET expires_at=:past"
        ), {"past": int(datetime.now(timezone.utc).timestamp()) - 1})
    assert confirm(challenge_flow, challenge) is None
    assert proof_count(challenge_flow) == 0


def test_five_bad_codes_close_challenge_and_enforce_real_account_lockout(challenge_flow):
    challenge = create(challenge_flow)
    totp = pyotp.TOTP(challenge_flow[2])
    now = datetime.now(timezone.utc).timestamp()
    valid = {totp.at(now + offset * 30) for offset in (-1, 0, 1)}
    bad = next(f"{n:06d}" for n in range(100) if f"{n:06d}" not in valid)
    for _ in range(5):
        assert confirm(challenge_flow, challenge, code=bad) is None
    with challenge_flow[0].connect() as db:
        assert db.scalar(sa.text(
            "SELECT failed_attempts FROM payment_action_challenges_test"
        )) == 5
    assert auth.get_user_by_id("stepup-owner")["locked_until"] is not None
    assert confirm(challenge_flow, challenge) is None
    assert proof_count(challenge_flow) == 0


def test_proof_write_failure_rolls_back_challenge_claim(challenge_flow):
    engine = challenge_flow[0]
    challenge = create(challenge_flow)

    def fail_proof_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO PAYMENT_ACTION_BOUND_PROOFS_TEST"):
            raise RuntimeError("synthetic proof write failure")

    sa.event.listen(engine, "before_cursor_execute", fail_proof_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic proof write failure"):
            confirm(challenge_flow, challenge)
    finally:
        sa.event.remove(engine, "before_cursor_execute", fail_proof_insert)
    with engine.connect() as db:
        assert db.scalar(sa.text(
            "SELECT consumed_at FROM payment_action_challenges_test"
        )) is None
    assert proof_count(challenge_flow) == 0
    assert confirm(challenge_flow, challenge)
    assert proof_count(challenge_flow) == 1


def test_two_confirmations_create_one_proof(challenge_flow):
    challenge = create(challenge_flow)
    start = Barrier(2)

    def attempt():
        start.wait(timeout=10)
        return confirm(challenge_flow, challenge)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt)
        b = pool.submit(attempt)
        outcomes = [a.result(timeout=20), b.result(timeout=20)]
    proofs = [proof for proof in outcomes if proof is not None]
    assert len(proofs) == 1
    assert proof_count(challenge_flow) == 1
    assert apply(challenge_flow, proofs[0])
    assert challenge_flow[3].changes == [ACTION]


def test_logout_prevents_challenge_confirmation(challenge_flow):
    challenge = create(challenge_flow)
    assert auth.revoke_access_token(challenge_flow[1])
    assert confirm(challenge_flow, challenge) is None
    assert proof_count(challenge_flow) == 0
    assert challenge_flow[3].changes == []
