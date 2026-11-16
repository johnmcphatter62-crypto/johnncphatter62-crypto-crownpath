"""Synthetic policy checks only; does not assert real MFA verification or atomic use."""
from datetime import datetime, timedelta, timezone

import pytest

from crownpath.payment_mfa_stepup_test_policy import fresh_payment_stepup

NOW = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)


def proof(**overrides):
    data = {"verified": True, "consumed": False, "user_id": "owner-a",
            "session_id": "session-a", "action": "change-payout",
            "verified_at": NOW - timedelta(seconds=30)}
    data.update(overrides)
    return data


def check(data):
    return fresh_payment_stepup(data, user_id="owner-a", session_id="session-a",
                                action="change-payout", now=NOW)


def test_recent_correct_owner_session_and_action():
    assert check(proof()) is True
    assert check(proof(verified_at=NOW - timedelta(seconds=120))) is True


@pytest.mark.parametrize("change", [
    {"verified": False}, {"verified": "true"}, {"consumed": True},
    {"user_id": "owner-b"}, {"session_id": "session-b"},
    {"action": "change-bank"},
    {"verified_at": NOW - timedelta(seconds=121)},
    {"verified_at": NOW + timedelta(seconds=1)},
    {"verified_at": NOW.replace(tzinfo=None)},
    {"verified_at": "2026-10-31"},
])
def test_wrong_stale_reused_or_untrusted_record_denied(change):
    assert check(proof(**change)) is False


def test_missing_record_and_bad_max_age_denied():
    assert check(None) is False
    assert fresh_payment_stepup(proof(), user_id="owner-a", session_id="session-a",
                                action="change-payout", now=NOW, max_age_seconds=1000) is False
