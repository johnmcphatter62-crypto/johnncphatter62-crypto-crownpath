"""Synthetic CrownPath wireless device idle-timeout checks.

No real wireless devices or production sessions are accessed.
"""
import pytest


MAX_IDLE_SECONDS = 300


def session_valid(session, now):
    if not session["approved"] or session["revoked"]:
        return False
    idle = now - session["last_activity"]
    return 0 <= idle < MAX_IDLE_SECONDS


@pytest.mark.parametrize("transport", ["bluetooth", "wifi"])
def test_recent_approved_session_is_valid(transport):
    session = {"transport": transport, "approved": True,
               "revoked": False, "last_activity": 100}
    assert session_valid(session, 200)


def test_session_expires_at_idle_limit():
    session = {"approved": True, "revoked": False, "last_activity": 100}
    assert not session_valid(session, 400)


def test_session_expires_after_idle_limit():
    session = {"approved": True, "revoked": False, "last_activity": 100}
    assert not session_valid(session, 401)


def test_revoked_session_cannot_resume():
    session = {"approved": True, "revoked": True, "last_activity": 100}
    assert not session_valid(session, 101)


def test_unapproved_session_is_denied():
    session = {"approved": False, "revoked": False, "last_activity": 100}
    assert not session_valid(session, 101)


def test_future_activity_timestamp_is_denied():
    session = {"approved": True, "revoked": False, "last_activity": 200}
    assert not session_valid(session, 100)
