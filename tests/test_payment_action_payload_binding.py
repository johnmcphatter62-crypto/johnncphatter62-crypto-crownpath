"""Fake-provider payload binding only; no real MFA, cookies, or payments."""
import pytest
import sqlalchemy as sa

from tests.payment_action_binding_fixture import (
    create_action_binding_test_schema, issue_for_verified_fixture,
    consume_for_verified_fixture,
)

OWNER = {"user_id": "synthetic-owner", "role": "OWNER", "active": True, "mfa_enabled": True}
KEY = b"synthetic-action-binding-test-key-only"
ACTION = {
    "action": "payments.configure", "provider_ref": "fake-provider-a",
    "destination_ref": "synthetic-destination-a", "currency": "USD",
}


class FakeProvider:
    def __init__(self):
        self.changes = []

    def configure(self, action):
        self.changes.append(dict(action))


@pytest.fixture
def fixture(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'action_binding.db'}")
    try:
        create_action_binding_test_schema(engine)
        approved = dict(ACTION)
        token = issue_for_verified_fixture(
            engine, user_id=OWNER["user_id"], session_id="synthetic-session",
            action=approved, key=KEY, now=100,
        )
        yield engine, token, FakeProvider(), approved
    finally:
        engine.dispose()


def request(fixture, **overrides):
    engine, token, provider, approved = fixture
    values = dict(
        user=OWNER, session_id="synthetic-session", token=token,
        action=approved, key=KEY, now=101, csrf_verified=True, session_active=True,
    )
    values.update(overrides)
    if not consume_for_verified_fixture(engine, **values):
        return False
    provider.configure(values["action"])
    return True


@pytest.mark.parametrize("change", [
    {"destination_ref": "synthetic-destination-b"},
    {"provider_ref": "fake-provider-b"},
    {"currency": "EUR"},
    {"action": "profile.edit"},
    {"extra": "unapproved"},
])
def test_changed_payload_denies_without_consuming_approved_proof(fixture, change):
    engine, token, provider, approved = fixture
    assert not request(fixture, action={**approved, **change})
    assert provider.changes == []
    assert request(fixture)
    assert provider.changes == [ACTION]
    assert not request(fixture)
    assert provider.changes == [ACTION]


@pytest.mark.parametrize("change", [
    {"user": {**OWNER, "user_id": "another-owner"}},
    {"session_id": "another-session"},
    {"csrf_verified": False},
    {"session_active": False},
    {"key": b"different-synthetic-key-material-32"},
])
def test_scope_or_policy_mismatch_does_not_burn_proof(fixture, change):
    assert not request(fixture, **change)
    assert fixture[2].changes == []
    assert request(fixture)
    assert fixture[2].changes == [ACTION]


def test_reordered_fields_match_and_raw_proof_is_not_stored(fixture):
    engine, token, provider, approved = fixture
    with engine.connect() as db:
        row = db.execute(sa.text(
            "SELECT proof_hash, action_digest FROM payment_action_bound_proofs_test"
        )).one()
        assert row.proof_hash != token
        assert token not in str(row)
        assert row.proof_hash != __import__("hashlib").sha256(token.encode()).hexdigest()
    reordered = dict(reversed(list(approved.items())))
    assert request(fixture, action=reordered)
    assert provider.changes == [ACTION]


def test_expiry_boundary_denies_without_provider_change(fixture):
    assert not request(fixture, now=220)
    assert fixture[2].changes == []
    with fixture[0].connect() as db:
        assert db.scalar(sa.text(
            "SELECT used_at FROM payment_action_bound_proofs_test"
        )) is None


def test_commit_failure_rolls_back_before_fake_provider_call(fixture):
    engine = fixture[0]

    def fail_commit(connection):
        raise RuntimeError("synthetic commit failure")

    sa.event.listen(engine, "commit", fail_commit)
    try:
        with pytest.raises(RuntimeError, match="synthetic commit failure"):
            request(fixture)
    finally:
        sa.event.remove(engine, "commit", fail_commit)
    assert fixture[2].changes == []
    with engine.connect() as db:
        assert db.scalar(sa.text(
            "SELECT used_at FROM payment_action_bound_proofs_test"
        )) is None
    assert request(fixture)
    assert fixture[2].changes == [ACTION]
