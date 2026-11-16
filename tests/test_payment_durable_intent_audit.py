"""Atomic authorization intent acceptance with real session/challenge/TOTP."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from threading import Barrier

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath import auth
from crownpath.models import AuditEvent
from tests.payment_intent_audit_fixture import create_intent_audit_test_schema, authorize_intent
from tests.payment_one_use_challenge_fixture import (
    create_action_challenge_test_schema, create_action_challenge, confirm_action_challenge,
)
from tests.payment_real_stepup_fixture import ORIGIN
from tests.test_payment_real_stepup_binding import real_stepup
from tests.test_payment_action_payload_binding import ACTION


@pytest.fixture
def intent_flow(real_stepup):
    import pyotp
    engine, cookie, secret, provider = real_stepup
    create_action_challenge_test_schema(engine)
    create_intent_audit_test_schema(engine)
    challenge = create_action_challenge(engine, cookie=cookie, action=dict(ACTION), origin=ORIGIN)
    proof = confirm_action_challenge(
        engine, cookie=cookie, challenge=challenge, action=dict(ACTION),
        code=pyotp.TOTP(secret).now(), origin=ORIGIN,
    )
    assert proof
    return real_stepup, proof


def authorize(fixture, **changes):
    base, proof = fixture
    values = dict(cookie=base[1], proof=proof, action=dict(ACTION), origin=ORIGIN)
    values.update(changes)
    return authorize_intent(base[0], **values)


def counts(fixture):
    engine = fixture[0][0]
    with engine.connect() as db:
        return (
            db.scalar(sa.text("SELECT count(*) FROM payment_authorized_intents_test")),
            db.scalar(sa.select(sa.func.count()).select_from(AuditEvent).where(
                AuditEvent.action == "PAYMENT_INTENT_AUTHORIZED",
            )),
        )


def test_authorization_retry_returns_one_durable_intent_and_audit(intent_flow):
    result = authorize(intent_flow)
    assert result and result["status"] == "PENDING"
    assert authorize(intent_flow) == result
    assert counts(intent_flow) == (1, 1)
    base, proof = intent_flow
    with Session(base[0]) as db:
        event = db.scalar(sa.select(AuditEvent).where(
            AuditEvent.action == "PAYMENT_INTENT_AUTHORIZED",
        ))
        assert event.user_id == "stepup-owner"
        assert event.resource_id == result["intent_id"]
        metadata = " ".join(str(getattr(event, name)) for name in (
            "action", "category", "resource_type", "resource_id", "result", "reason",
        ))
        for sensitive in (proof, base[1], base[2], auth.SECRET_KEY):
            assert sensitive not in metadata
    assert base[3].changes == []  # Authorization is not provider dispatch.


@pytest.mark.parametrize("failed_table", ["PAYMENT_AUTHORIZED_INTENTS_TEST", "AUDIT_EVENTS"])
def test_write_failure_rolls_back_proof_intent_and_audit(intent_flow, failed_table):
    engine = intent_flow[0][0]

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO " + failed_table):
            raise RuntimeError("synthetic intent/audit write failure")

    sa.event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(RuntimeError, match="synthetic intent/audit write failure"):
            authorize(intent_flow)
    finally:
        sa.event.remove(engine, "before_cursor_execute", fail_insert)
    assert counts(intent_flow) == (0, 0)
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT used_at FROM payment_action_bound_proofs_test")) is None
    assert authorize(intent_flow)
    assert counts(intent_flow) == (1, 1)
    assert intent_flow[0][3].changes == []


def test_changed_payload_cannot_create_intent_or_retrieve_receipt(intent_flow):
    changed = {**ACTION, "destination_ref": "synthetic-destination-b"}
    assert authorize(intent_flow, action=changed) is None
    assert counts(intent_flow) == (0, 0)
    result = authorize(intent_flow)
    assert result
    assert authorize(intent_flow, action=changed) is None
    assert authorize(intent_flow) == result
    assert counts(intent_flow) == (1, 1)


def test_competing_authorizations_return_same_receipt(intent_flow):
    start = Barrier(2)

    def attempt():
        start.wait(timeout=10)
        return authorize(intent_flow)

    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(attempt)
        b = pool.submit(attempt)
        results = [a.result(timeout=20), b.result(timeout=20)]
    assert results[0] and results[0] == results[1]
    assert counts(intent_flow) == (1, 1)
    assert intent_flow[0][3].changes == []


def test_logout_denies_access_to_prior_intent_receipt(intent_flow):
    assert authorize(intent_flow)
    assert auth.revoke_access_token(intent_flow[0][1])
    assert authorize(intent_flow) is None
    assert counts(intent_flow) == (1, 1)


def test_intent_keeps_authorized_snapshot_after_original_changes(intent_flow):
    original = deepcopy(ACTION)
    receipt = authorize(intent_flow, action=original)
    assert receipt
    original["destination_ref"] = "synthetic-destination-b"
    with intent_flow[0][0].connect() as db:
        saved = db.scalar(sa.text(
            "SELECT action_json FROM payment_authorized_intents_test WHERE intent_id=:intent"
        ), {"intent": receipt["intent_id"]})
    assert json.loads(saved) == ACTION
    assert authorize(intent_flow, action=original) is None
    assert counts(intent_flow) == (1, 1)


def test_expired_proof_cannot_create_durable_intent(intent_flow):
    with intent_flow[0][0].begin() as db:
        db.execute(sa.text("UPDATE payment_action_bound_proofs_test SET expires_at=0"))
    assert authorize(intent_flow) is None
    assert counts(intent_flow) == (0, 0)
