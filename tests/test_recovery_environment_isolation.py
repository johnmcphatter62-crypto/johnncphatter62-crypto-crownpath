"""Synthetic recovery environment isolation checks.

Only fictional bytes are used. Production restore needs independent approval.
"""
import hashlib
import hmac

import pytest


def sign_backup(data, environment, key):
    digest = hashlib.sha256(data).hexdigest()
    signed = f"{environment}:{digest}".encode()
    return {"environment": environment, "digest": digest,
            "signature": hmac.new(key, signed, hashlib.sha256).hexdigest()}


def verify_backup(data, manifest, target_environment, key):
    signed = f"{manifest['environment']}:{manifest['digest']}".encode()
    expected = hmac.new(key, signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, manifest["signature"]):
        raise ValueError("Invalid manifest signature")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), manifest["digest"]):
        raise ValueError("Invalid backup content")
    if manifest["environment"] != target_environment:
        raise ValueError("Recovery environment mismatch")
    return True


KEY = b"fictional-key"
DATA = b"fictional-curriculum"


def test_matching_environment():
    manifest = sign_backup(DATA, "test", KEY)
    assert verify_backup(DATA, manifest, "test", KEY)


def test_test_backup_rejected_in_production():
    manifest = sign_backup(DATA, "test", KEY)
    with pytest.raises(ValueError, match="environment mismatch"):
        verify_backup(DATA, manifest, "production", KEY)


def test_changed_environment_label_rejected():
    manifest = sign_backup(DATA, "test", KEY)
    manifest["environment"] = "production"
    with pytest.raises(ValueError, match="Invalid manifest signature"):
        verify_backup(DATA, manifest, "production", KEY)


def test_changed_backup_content_rejected():
    manifest = sign_backup(DATA, "test", KEY)
    with pytest.raises(ValueError, match="Invalid backup content"):
        verify_backup(b"changed", manifest, "test", KEY)
