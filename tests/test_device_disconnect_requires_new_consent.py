"""Synthetic CrownPath device disconnection and media restart tests.

No real camera, microphone, Bluetooth, or Wi-Fi hardware is used.
"""
import pytest


def may_stream(session):
    return (
        session["connected"]
        and session["consented"]
        and session["consent_generation"] == session["connection_generation"]
    )


@pytest.mark.parametrize("media_type", ["camera", "microphone"])
def test_connected_session_with_fresh_consent(media_type):
    session = {"media_type": media_type, "connected": True,
               "consented": True, "connection_generation": 1,
               "consent_generation": 1}
    assert may_stream(session)


def test_disconnected_session_cannot_stream():
    session = {"connected": False, "consented": True,
               "connection_generation": 1, "consent_generation": 1}
    assert not may_stream(session)


def test_reconnect_cannot_reuse_old_consent():
    session = {"connected": True, "consented": True,
               "connection_generation": 2, "consent_generation": 1}
    assert not may_stream(session)


def test_reconnect_with_new_consent_can_stream():
    session = {"connected": True, "consented": True,
               "connection_generation": 2, "consent_generation": 2}
    assert may_stream(session)


def test_explicit_consent_denial_blocks_stream():
    session = {"connected": True, "consented": False,
               "connection_generation": 2, "consent_generation": 2}
    assert not may_stream(session)
