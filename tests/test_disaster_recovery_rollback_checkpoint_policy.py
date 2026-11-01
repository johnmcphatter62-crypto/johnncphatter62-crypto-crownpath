"""Recovery rollback gate using independently trusted recovery sequence.

This is a synthetic policy test. Production requires an authenticated,
durable high-water mark stored outside the backup and separate key custody.
"""
import hashlib
import hmac

import pytest


def manifest(data: bytes, sequence: int, key: bytes):
    digest = hashlib.sha256(data).hexdigest()
    message = f"{sequence}:{digest}".encode()
    return {"sequence": sequence, "sha256": digest,
            "signature": hmac.new(key, message, hashlib.sha256).hexdigest()}


def verify(data: bytes, record: dict, key: bytes, minimum_sequence: int):
    message = f"{record['sequence']}:{record['sha256']}".encode()
    signature = hmac.new(key, message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, record["signature"]):
        raise ValueError("Untrusted recovery manifest")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), record["sha256"]):
        raise ValueError("Modified recovery data")
    if record["sequence"] < minimum_sequence:
        raise ValueError("Backup rollback detected")
    return True


def test_latest_authentic_backup_passes():
    key = b"fictional-test-only-key"
    data = b"fictional student progress version 8"
    assert verify(data, manifest(data, 8, key), key, minimum_sequence=8)


def test_older_authentic_backup_rejected_against_external_checkpoint():
    key = b"fictional-test-only-key"
    old = b"fictional student progress version 5"
    with pytest.raises(ValueError, match="rollback"):
        verify(old, manifest(old, 5, key), key, minimum_sequence=8)


def test_relabeling_old_backup_with_new_sequence_invalidates_signature():
    key = b"fictional-test-only-key"
    old = b"fictional student progress version 5"
    record = manifest(old, 5, key)
    record["sequence"] = 8
    with pytest.raises(ValueError, match="Untrusted"):
        verify(old, record, key, minimum_sequence=8)


def test_modified_backup_rejected_even_when_sequence_is_current():
    key = b"fictional-test-only-key"
    original = b"fictional student progress version 8"
    with pytest.raises(ValueError, match="Modified"):
        verify(b"tampered", manifest(original, 8, key), key, minimum_sequence=8)
