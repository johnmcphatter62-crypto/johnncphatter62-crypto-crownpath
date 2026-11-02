"""Synthetic CrownPath camera and microphone consent checks.

No camera, microphone, Bluetooth, or Wi-Fi device is accessed.
"""
import pytest


def can_start_media(request, permission):
    return (
        request["user_id"] == permission["user_id"]
        and request["device_id"] == permission["device_id"]
        and request["media_type"] == permission["media_type"]
        and permission["consented"]
        and not permission["revoked"]
    )


@pytest.mark.parametrize("media_type", ["camera", "microphone"])
def test_matching_explicit_consent_allows_media(media_type):
    request = {"user_id": "learner-a", "device_id": "demo-device",
               "media_type": media_type}
    permission = dict(request, consented=True, revoked=False)
    assert can_start_media(request, permission)


def test_missing_consent_denies_camera():
    request = {"user_id": "learner-a", "device_id": "demo-device",
               "media_type": "camera"}
    permission = dict(request, consented=False, revoked=False)
    assert not can_start_media(request, permission)


def test_revoked_consent_denies_microphone():
    request = {"user_id": "learner-a", "device_id": "demo-device",
               "media_type": "microphone"}
    permission = dict(request, consented=True, revoked=True)
    assert not can_start_media(request, permission)


def test_camera_consent_does_not_authorize_microphone():
    request = {"user_id": "learner-a", "device_id": "demo-device",
               "media_type": "microphone"}
    permission = dict(request, media_type="camera", consented=True,
                      revoked=False)
    assert not can_start_media(request, permission)


def test_other_users_consent_cannot_be_reused():
    request = {"user_id": "learner-b", "device_id": "demo-device",
               "media_type": "camera"}
    permission = dict(request, user_id="learner-a", consented=True,
                      revoked=False)
    assert not can_start_media(request, permission)


def test_other_device_consent_cannot_be_reused():
    request = {"user_id": "learner-a", "device_id": "device-b",
               "media_type": "camera"}
    permission = dict(request, device_id="device-a", consented=True,
                      revoked=False)
    assert not can_start_media(request, permission)
