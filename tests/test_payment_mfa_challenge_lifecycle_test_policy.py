"""Synthetic payment-specific MFA challenge lifecycle policy tests.

No authenticator codes, live payment endpoints, or production credentials.
"""
from datetime import datetime, timedelta, timezone

import pytest

from crownpath.payment_mfa_challenge_lifecycle_test_policy import (
    eligible_payment_challenge,
)

NOW = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)


def challenge(**overrides):
    data = {
        "user_id": "owner-a", "session_id": "session-a",
        "action": "payments.configure", "server_issued": True,
        "verified": True, "consumed": False, "failed_attempts": 0,
        "verified_at": NOW - timedelta(seconds=30),
    }
    data.update(overrides)
    return data


def eligible(record, **overrides):
    args = {
        "user_id": "owner-a", "session_id": "session-a",
        "action": "payments.configure", "now": NOW,
    }
    args.update(overrides)
    return eligible_payment_challenge(record, **args)


def test_valid_fresh_challenge_and_near_expiry():
    assert eligible(challenge())
    assert eligible(challenge(verified_at=NOW - timedelta(seconds=119)))
    assert eligible(challenge(failed_attempts=4))


@pytest.mark.parametrize("changes", [
    {"server_issued": False}, {"server_issued": "true"},
    {"verified": False}, {"verified": "true"},
    {"consumed": True}, {"failed_attempts": 5},
    {"failed_attempts": -1}, {"failed_attempts": True},
    {"failed_attempts": "0"}, {"user_id": "owner-b"},
    {"session_id": "session-b"}, {"action": "payments.refund"},
    {"verified_at": NOW - timedelta(seconds=120)},
    {"verified_at": NOW + timedelta(seconds=1)},
    {"verified_at": NOW.replace(tzinfo=None)},
    {"verified_at": "not-a-datetime"},
])
def test_invalid_replayed_expired_or_mismatched_challenge_denied(changes):
    assert not eligible(challenge(**changes))


def test_missing_challenge_and_invalid_configuration_denied():
    assert not eligible(None)
    assert not eligible(challenge(), max_age_seconds=0)
    assert not eligible(challenge(), max_age_seconds=301)
    assert not eligible(challenge(), max_failures=0)
    assert not eligible(challenge(), max_failures=11)
    assert not eligible(challenge(), max_failures=True)
    assert not eligible(challenge(), now=NOW.replace(tzinfo=None))
