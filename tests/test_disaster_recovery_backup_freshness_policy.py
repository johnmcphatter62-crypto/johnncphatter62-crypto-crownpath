"""Recovery policy rejects stale or future-dated authenticated backups.

Synthetic artifacts only. Production timestamps must be authenticated and
checked against independently trusted time and recovery-point objectives.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac

import pytest


def _signed_manifest(data, captured_at, key):
    digest = hashlib.sha256(data).hexdigest()
    stamp = captured_at.isoformat()
    message = f"{digest}|{stamp}".encode("utf-8")
    return {"sha256": digest, "captured_at": stamp,
            "signature": hmac.new(key, message, hashlib.sha256).hexdigest()}


def _check_backup(data, manifest, key, now, max_age):
    digest = hashlib.sha256(data).hexdigest()
    message = f"{manifest['sha256']}|{manifest['captured_at']}".encode("utf-8")
    expected = hmac.new(key, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, manifest["signature"]):
        raise ValueError("Invalid manifest signature")
    if not hmac.compare_digest(digest, manifest["sha256"]):
        raise ValueError("Backup content mismatch")
    captured = datetime.fromisoformat(manifest["captured_at"])
    if captured.tzinfo is None:
        raise ValueError("Untrusted timestamp without timezone")
    age = now - captured.astimezone(timezone.utc)
    if age < timedelta(0):
        raise ValueError("Future-dated backup")
    if age > max_age:
        raise ValueError("Stale backup")
    return True


def test_recent_authenticated_backup_is_eligible():
    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    key = b"synthetic-only-recovery-key"
    data = b"fictional classroom progress"
    manifest = _signed_manifest(data, now - timedelta(minutes=10), key)
    assert _check_backup(data, manifest, key, now, timedelta(hours=1))


def test_old_authenticated_backup_is_rejected():
    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    key = b"synthetic-only-recovery-key"
    data = b"fictional classroom progress"
    manifest = _signed_manifest(data, now - timedelta(days=2), key)
    with pytest.raises(ValueError, match="Stale backup"):
        _check_backup(data, manifest, key, now, timedelta(hours=1))


def test_future_dated_backup_is_rejected():
    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    key = b"synthetic-only-recovery-key"
    data = b"fictional classroom progress"
    manifest = _signed_manifest(data, now + timedelta(minutes=2), key)
    with pytest.raises(ValueError, match="Future-dated backup"):
        _check_backup(data, manifest, key, now, timedelta(hours=1))


def test_tampering_with_timestamp_breaks_signature():
    now = datetime(2026, 11, 1, 12, tzinfo=timezone.utc)
    key = b"synthetic-only-recovery-key"
    data = b"fictional classroom progress"
    manifest = _signed_manifest(data, now - timedelta(days=2), key)
    manifest["captured_at"] = now.isoformat()
    with pytest.raises(ValueError, match="Invalid manifest signature"):
        _check_backup(data, manifest, key, now, timedelta(hours=1))
