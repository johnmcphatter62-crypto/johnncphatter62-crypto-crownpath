"""Isolated JWT and revocation checks; no real sessions or production data."""
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session

SECRET = "test-only-signing-secret"
ALG = "HS256"


def token(*, secret=SECRET, purpose="session", user="owner", session="s1", expires=60):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user, "jti": session, "purpose": purpose,
         "exp": now + timedelta(seconds=expires)},
        secret, algorithm=ALG,
    )


def validate(value, *, active_sessions=None, active_users=None):
    sessions = {("owner", "s1")} if active_sessions is None else active_sessions
    users = {"owner"} if active_users is None else active_users
    return validate_signed_session(
        value, secret=SECRET, algorithm=ALG,
        active_session=lambda u, s: (u, s) in sessions,
        active_user=lambda u: u in users,
    )


def test_valid_signed_active_session():
    assert validate(token()) == {"user_id": "owner", "session_id": "s1"}


@pytest.mark.parametrize("value", [
    None, "", "invalid-token", token(secret="attacker"),
    token(purpose="mfa_challenge"), token(expires=-60),
    token(user="attacker"), token(session="different"),
])
def test_untrusted_or_inactive_session_rejected(value):
    assert validate(value) is None


def test_revoked_session_rejected():
    signed = token()
    assert validate(signed) is not None
    assert validate(signed, active_sessions=set()) is None


def test_disabled_user_rejected():
    assert validate(token(), active_users=set()) is None


def test_authoritative_database_failure_fails_closed():
    def broken(*_):
        raise RuntimeError("database unavailable")
    assert validate_signed_session(
        token(), secret=SECRET, algorithm=ALG,
        active_session=broken, active_user=lambda _: True,
    ) is None
