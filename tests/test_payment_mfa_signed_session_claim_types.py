"""Reject malformed JWT claim types in isolated payment session adapter."""
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from crownpath.payment_mfa_signed_session_test_adapter import validate_signed_session

SECRET = "claim-type-test-secret"


@pytest.mark.parametrize("claim, value", [
    ("sub", None), ("sub", 42), ("sub", []), ("sub", " "),
    ("jti", None), ("jti", 42), ("jti", []), ("jti", " "),
    ("purpose", None), ("purpose", "payment"),
])
def test_malformed_signed_claims_fail_before_database_lookup(claim, value):
    payload = {
        "sub": "owner", "jti": "s1", "purpose": "session",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    payload[claim] = value
    signed = jwt.encode(payload, SECRET, algorithm="HS256")
    calls = []
    result = validate_signed_session(
        signed, secret=SECRET, algorithm="HS256",
        active_session=lambda *_: calls.append("session") or True,
        active_user=lambda *_: calls.append("user") or True,
    )
    assert result is None
    assert calls == []
