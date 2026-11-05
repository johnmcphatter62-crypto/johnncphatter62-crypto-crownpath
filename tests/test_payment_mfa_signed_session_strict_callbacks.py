"""Fail-closed callback shape tests for isolated signed-session adapter."""
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session

SECRET = "isolated-test-secret"
ALG = "HS256"


def signed():
    return jwt.encode({
        "sub": "owner", "jti": "session-a", "purpose": "session",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }, SECRET, algorithm=ALG)


@pytest.mark.parametrize("session_result", [None, False, 0, 1, "yes", [], {}])
def test_only_explicit_true_session_assertion_accepted(session_result):
    assert validate_signed_session(
        signed(), secret=SECRET, algorithm=ALG,
        active_session=lambda *_: session_result,
        active_user=lambda _: True,
    ) is None


@pytest.mark.parametrize("user_result", [None, False, 0, 1, "yes", [], {}])
def test_only_explicit_true_user_assertion_accepted(user_result):
    assert validate_signed_session(
        signed(), secret=SECRET, algorithm=ALG,
        active_session=lambda *_: True,
        active_user=lambda _: user_result,
    ) is None
