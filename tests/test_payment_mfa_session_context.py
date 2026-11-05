"""Unit checks for the isolated session-context scaffold."""
import pytest
from crownpath.payment_mfa_session_context import verified_session_context


@pytest.mark.parametrize("token", [None, "", "  ", 123, {}, []])
def test_invalid_token_does_not_call_validator(token):
    calls = []
    assert verified_session_context(
        token, decode_and_check=lambda _: calls.append(1)
    ) is None
    assert calls == []


@pytest.mark.parametrize("claims", [
    None, "claims", {}, {"user_id": "owner"},
    {"session_id": "s1"}, {"user_id": " ", "session_id": "s1"},
    {"user_id": "owner", "session_id": " "},
    {"user_id": 7, "session_id": "s1"},
])
def test_invalid_validated_claims_fail_closed(claims):
    assert verified_session_context(
        "signed-token", decode_and_check=lambda _: claims
    ) is None


def test_validated_claims_return_identity_pair():
    assert verified_session_context(
        "signed-token",
        decode_and_check=lambda _: {"user_id": "owner", "session_id": "s1"},
    ) == ("owner", "s1")


def test_validator_failure_fails_closed():
    def rejected(_):
        raise ValueError("revoked or expired")
    assert verified_session_context(
        "signed-token", decode_and_check=rejected
    ) is None
