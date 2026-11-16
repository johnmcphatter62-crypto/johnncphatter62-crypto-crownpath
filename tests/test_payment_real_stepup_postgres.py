"""Run authoritative session/TOTP acceptance on disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock

import pyotp
import pytest
from sqlalchemy.orm import Session, sessionmaker

from crownpath import auth
from crownpath.models import User
from tests import test_payment_real_stepup_binding as checks
from tests.payment_action_binding_fixture import create_action_binding_test_schema
from tests.payment_real_stepup_fixture import ORIGIN, consume_from_real_session
from tests.test_payment_action_payload_binding import ACTION, FakeProvider
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


@pytest.fixture
def real_stepup_postgres(isolated_logout_engine, monkeypatch):
    engine = isolated_logout_engine
    monkeypatch.setattr(auth, "session", sessionmaker(bind=engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-real-postgres-stepup-secret-key-2026")
    create_action_binding_test_schema(engine)
    secret = pyotp.random_base32()
    with Session(engine) as db:
        db.add(User(
            user_id="stepup-owner", name="Synthetic Owner",
            email="stepup-owner@example.invalid", password_hash="synthetic-only",
            role="OWNER", active=True, mfa_enabled=True, mfa_secret=secret,
        ))
        db.commit()
    cookie = auth.create_access_token("stepup-owner", mfa_verified=True)
    return engine, cookie, secret, FakeProvider()


@pytest.mark.parametrize("failure", ["unverified-session", "forged-session", "wrong-code", "wrong-origin"])
def test_postgres_real_session_and_fresh_code_required(real_stepup_postgres, failure):
    checks.test_real_stepup_issue_requires_actual_session_and_mfa(real_stepup_postgres, failure)


@pytest.mark.parametrize("change", [{"role": "BARBER"}, {"active": False}, {"mfa_enabled": False}])
def test_postgres_owner_eligibility_before_issue(real_stepup_postgres, change):
    checks.test_real_stepup_rechecks_owner_before_issuance(real_stepup_postgres, change)


def test_postgres_verified_action_scope_and_replay(real_stepup_postgres):
    checks.test_verified_action_rejects_other_session_and_payload_then_applies_once(real_stepup_postgres)


def test_postgres_logout_revokes_action_authority(real_stepup_postgres):
    checks.test_real_logout_invalidates_action_proof_authority(real_stepup_postgres)


@pytest.mark.parametrize("change", [{"role": "BARBER"}, {"active": False}, {"mfa_enabled": False}])
def test_postgres_owner_state_rechecked_before_use(real_stepup_postgres, change):
    checks.test_role_or_account_change_before_consumption_denies(real_stepup_postgres, change)


def test_postgres_payment_permission_required(real_stepup_postgres, monkeypatch):
    checks.test_canonical_payment_permission_is_required_at_issue_and_use(real_stepup_postgres, monkeypatch)


def test_postgres_real_session_eight_consumers_one_winner(real_stepup_postgres):
    engine, cookie, secret, provider = real_stepup_postgres
    proof = checks.issue(real_stepup_postgres)
    assert proof
    start = Barrier(8)
    dispatch = Lock()

    def consume():
        start.wait(timeout=10)
        snapshot = dict(ACTION)
        allowed = consume_from_real_session(
            engine, cookie=cookie, proof=proof, action=snapshot, origin=ORIGIN,
        )
        if allowed:
            with dispatch:
                provider.configure(snapshot)
        return allowed

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(consume) for _ in range(8)]
        results = [future.result(timeout=20) for future in futures]
    assert results.count(True) == 1
    assert results.count(False) == 7
    assert provider.changes == [ACTION]
    assert not checks.apply(real_stepup_postgres, proof)
    assert auth.decode_access_token(cookie) == "stepup-owner"
