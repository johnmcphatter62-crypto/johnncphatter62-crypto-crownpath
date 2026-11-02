"""Synthetic CrownPath media consent and session binding tests.

No real camera or microphone is accessed.
"""
import pytest


def media_allowed(request, consent):
    return (
        consent["granted"]
        and not consent["revoked"]
        and request["session_id"] == consent["session_id"]
        and request["device_id"] == consent["device_id"]
        and request["user_id"] == consent["user_id"]
        and request["media_type"] == consent["media_type"]
    )


@pytest.mark.parametrize("media_type", ["camera", "microphone"])
def test_matching_session_consent(media_type):
    request = {"session_id": "session-a", "device_id": "device-a",
               "user_id": "learner-a", "media_type": media_type}
    assert media_allowed(request, dict(request, granted=True, revoked=False))


def test_previous_session_consent_is_denied():
    request = {"session_id": "session-b", "device_id": "device-a",
               "user_id": "learner-a", "media_type": "camera"}
    consent = dict(request, session_id="session-a", granted=True, revoked=False)
    assert not media_allowed(request, consent)


def test_revoked_session_consent_is_denied():
    request = {"session_id": "session-a", "device_id": "device-a",
               "user_id": "learner-a", "media_type": "microphone"}
    assert not media_allowed(request, dict(request, granted=True, revoked=True))


def test_other_device_session_consent_is_denied():
    request = {"session_id": "session-a", "device_id": "device-b",
               "user_id": "learner-a", "media_type": "camera"}
    consent = dict(request, device_id="device-a", granted=True, revoked=False)
    assert not media_allowed(request, consent)


def test_missing_grant_is_denied():
    request = {"session_id": "session-a", "device_id": "device-a",
               "user_id": "learner-a", "media_type": "camera"}
    assert not media_allowed(request, dict(request, granted=False, revoked=False))
