"""Recovery gate rejects modified classroom backups before any restore.

Synthetic SQLite only. Hash manifest is a local integrity check, not an
authenticated signature; production requires trusted external manifest storage.
"""
import hashlib
import shutil
import sqlite3

import pytest


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_restore(backup, expected_digest, destination):
    if _sha256(backup) != expected_digest:
        raise ValueError("Backup integrity verification failed")
    shutil.copyfile(backup, destination)


def test_verified_backup_restores_fictional_classroom(tmp_path):
    backup = tmp_path / "backup.db"
    recovered = tmp_path / "recovered.db"
    with sqlite3.connect(backup) as db:
        db.execute("CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT)")
        db.execute("INSERT INTO lessons VALUES (?, ?)", ("fictional", "Synthetic class"))
    expected = _sha256(backup)
    _verified_restore(backup, expected, recovered)
    with sqlite3.connect(recovered) as db:
        assert db.execute("SELECT title FROM lessons WHERE id='fictional'").fetchone() == (
            "Synthetic class",)


def test_tampered_backup_is_rejected_before_restore(tmp_path):
    backup = tmp_path / "backup.db"
    recovered = tmp_path / "recovered.db"
    with sqlite3.connect(backup) as db:
        db.execute("CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT)")
        db.execute("INSERT INTO lessons VALUES (?, ?)", ("fictional", "Original"))
    trusted_digest = _sha256(backup)
    with sqlite3.connect(backup) as db:
        db.execute("UPDATE lessons SET title='Altered' WHERE id='fictional'")
    assert _sha256(backup) != trusted_digest
    with pytest.raises(ValueError, match="integrity"):
        _verified_restore(backup, trusted_digest, recovered)
    assert not recovered.exists()
