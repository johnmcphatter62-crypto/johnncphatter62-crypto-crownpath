"""Real-issued sessions and real TOTP verification; fake provider and SQLite only."""
from copy import deepcopy
from datetime import datetime, timezone

import jwt
import pyotp
import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from crownpath import auth
from crownpath.db_engine import Base
from crownpath.models import User
from tests.payment_action_binding_fixture import create_action_binding_test_schema
from tests.payment_real_stepup_fixture import (
    ORIGIN, issue_from_real_session, consume_from_real_session,
)
from tests.test_payment_action_payload_binding import ACTION, FakeProvider


@pytest.fixture
def real_stepup(tmp_path, monkeypatch):
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'real_stepup.db'}", connect_args={"timeout": 15},
    )
    monkeypatch.setattr(auth, "session", sessionmaker(bind=engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-real-stepup-fixture-secret-key-2026")
    try:
        Base.metadata.create_all(engine)
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
        yield engine, cookie, secret, FakeProvider()
    finally:
        engine.dispose()


def issue(fixture, **changes):
    engine, cookie, secret, provider = fixture
    values = dict(cookie=cookie, action=dict(ACTION), code=pyotp.TOTP(secret).now(), origin=ORIGIN)
    values.update(changes)
    return issue_from_real_session(engine, **values)


def apply(fixture, proof, **changes):
    engine, cookie, secret, provider = fixture
    values = dict(cookie=cookie, proof=proof, action=dict(ACTION), origin=ORIGIN)
    values.update(changes)
    values["action"] = deepcopy(values["action"])
    allowed = consume_from_real_session(engine, **values)
    if allowed:
        provider.configure(values["action"])
    return allowed


@pytest.mark.parametrize("failure", ["unverified-session", "forged-session", "wrong-code", "wrong-origin"])
def test_real_stepup_issue_requires_actual_session_and_mfa(real_stepup, failure):
    engine, cookie, secret, provider = real_stepup
    changes = {}
    if failure == "unverified-session":
        changes["cookie"] = auth.create_access_token("stepup-owner")
    elif failure == "forged-session":
        claims = jwt.decode(cookie, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        changes["cookie"] = jwt.encode(claims, "wrong-synthetic-signing-key-2026", algorithm=auth.ALGORITHM)
    elif failure == "wrong-code":
        totp = pyotp.TOTP(secret)
        now = datetime.now(timezone.utc).timestamp()
        valid = {totp.at(now + offset * 30) for offset in (-1, 0, 1)}
        changes["code"] = next(f"{n:06d}" for n in range(100) if f"{n:06d}" not in valid)
    else:
        changes["origin"] = "https://untrusted.example"
    assert issue(real_stepup, **changes) is None
    assert provider.changes == []
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT count(*) FROM payment_action_bound_proofs_test")) == 0
    if failure == "wrong-code":
        assert auth.get_user_by_id("stepup-owner")["failed_login_attempts"] == 1


@pytest.mark.parametrize("change", [{"role": "BARBER"}, {"active": False}, {"mfa_enabled": False}])
def test_real_stepup_rechecks_owner_before_issuance(real_stepup, change):
    engine, cookie, secret, provider = real_stepup
    with engine.begin() as db:
        db.execute(sa.update(User).where(User.user_id == "stepup-owner").values(**change))
    assert issue(real_stepup) is None
    assert provider.changes == []


def test_verified_action_rejects_other_session_and_payload_then_applies_once(real_stepup):
    engine, cookie, secret, provider = real_stepup
    proof = issue(real_stepup)
    assert proof
    other = auth.create_access_token("stepup-owner", mfa_verified=True)
    assert not apply(real_stepup, proof, cookie=other)
    assert not apply(real_stepup, proof, action={**ACTION, "destination_ref": "synthetic-destination-b"})
    assert provider.changes == []
    assert apply(real_stepup, proof)
    assert provider.changes == [ACTION]
    assert not apply(real_stepup, proof)
    assert provider.changes == [ACTION]


def test_real_logout_invalidates_action_proof_authority(real_stepup):
    proof = issue(real_stepup)
    assert proof
    assert auth.revoke_access_token(real_stepup[1])
    assert not apply(real_stepup, proof)
    assert real_stepup[3].changes == []


@pytest.mark.parametrize("change", [{"role": "BARBER"}, {"active": False}, {"mfa_enabled": False}])
def test_role_or_account_change_before_consumption_denies(real_stepup, change):
    engine, cookie, secret, provider = real_stepup
    proof = issue(real_stepup)
    assert proof
    with engine.begin() as db:
        db.execute(sa.update(User).where(User.user_id == "stepup-owner").values(**change))
    assert not apply(real_stepup, proof)
    assert provider.changes == []
    with engine.connect() as db:
        assert db.scalar(sa.text("SELECT used_at FROM payment_action_bound_proofs_test")) is None
