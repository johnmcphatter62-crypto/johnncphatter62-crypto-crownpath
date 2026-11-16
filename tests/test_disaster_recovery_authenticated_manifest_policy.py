"""Recovery verification with a trusted HMAC manifest held outside the backup.

Synthetic classroom data only. Production must use a managed secret store,
key rotation, access logging and an independently secured recovery location.
"""
import hashlib
import hmac
import json
import shutil

import pytest


def _manifest(backup_bytes, key):
    digest = hashlib.sha256(backup_bytes).hexdigest()
    signature = hmac.new(key, digest.encode("ascii"), hashlib.sha256).hexdigest()
    return {"sha256": digest, "hmac_sha256": signature}


def _verified_restore(backup, manifest, key, destination):
    actual_digest = hashlib.sha256(backup.read_bytes()).hexdigest()
    expected_signature = hmac.new(
        key, manifest["sha256"].encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, manifest["hmac_sha256"]):
        raise ValueError("Untrusted recovery manifest")
    if not hmac.compare_digest(actual_digest, manifest["sha256"]):
        raise ValueError("Modified backup")
    shutil.copyfile(backup, destination)


def test_trusted_manifest_allows_intact_classroom_backup(tmp_path):
    backup = tmp_path / "classroom.backup"
    restored = tmp_path / "restored.backup"
    key = b"synthetic-recovery-key-not-for-production"
    backup.write_bytes(b"fictional curriculum and progress")
    manifest = _manifest(backup.read_bytes(), key)
    _verified_restore(backup, manifest, key, restored)
    assert restored.read_bytes() == backup.read_bytes()


def test_replaced_backup_and_recomputed_checksum_cannot_forge_manifest(tmp_path):
    backup = tmp_path / "classroom.backup"
    restored = tmp_path / "restored.backup"
    key = b"synthetic-recovery-key-not-for-production"
    backup.write_bytes(b"fictional curriculum and progress")
    trusted = _manifest(backup.read_bytes(), key)
    backup.write_bytes(b"attacker-replaced-backup")
    attacker_manifest = {
        "sha256": hashlib.sha256(backup.read_bytes()).hexdigest(),
        "hmac_sha256": trusted["hmac_sha256"],
    }
    with pytest.raises(ValueError, match="Untrusted recovery manifest"):
        _verified_restore(backup, attacker_manifest, key, restored)
    assert not restored.exists()


def test_manifest_signature_cannot_be_modified_to_authorize_altered_backup(tmp_path):
    backup = tmp_path / "classroom.backup"
    restored = tmp_path / "restored.backup"
    key = b"synthetic-recovery-key-not-for-production"
    backup.write_bytes(b"original")
    manifest = _manifest(backup.read_bytes(), key)
    manifest = json.loads(json.dumps(manifest))
    manifest["hmac_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Untrusted recovery manifest"):
        _verified_restore(backup, manifest, key, restored)
    assert not restored.exists()
