"""Offline synthetic CrownPath recovery smoke test.

Uses only disposable SQLite files and fictional curriculum records.
Does not access production data, external services, or AI providers.
"""
import hashlib
import sqlite3
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_disposable_curriculum_database_backup_and_restore(tmp_path):
    original = tmp_path / "synthetic_source.sqlite3"
    backup = tmp_path / "synthetic_backup.sqlite3"
    restored = tmp_path / "synthetic_restored.sqlite3"

    with sqlite3.connect(original) as db:
        db.execute("CREATE TABLE lessons (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
        db.executemany("INSERT INTO lessons(id, title) VALUES (?, ?)", [
            (1, "Synthetic scalp care introduction"),
            (2, "Synthetic barber safety lesson"),
        ])
        db.commit()
        with sqlite3.connect(backup) as target:
            db.backup(target)

    expected_hash = digest(backup)
    assert expected_hash
    restored.write_bytes(backup.read_bytes())
    assert digest(restored) == expected_hash

    with sqlite3.connect(restored) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        lessons = db.execute("SELECT id, title FROM lessons ORDER BY id").fetchall()
        assert lessons == [
            (1, "Synthetic scalp care introduction"),
            (2, "Synthetic barber safety lesson"),
        ]

    with sqlite3.connect(original) as db:
        db.execute("DELETE FROM lessons")
        db.commit()

    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0] == 2


def test_corrupted_backup_fails_integrity_manifest(tmp_path):
    backup = tmp_path / "synthetic_backup.bin"
    backup.write_bytes(b"synthetic curriculum export")
    expected_hash = digest(backup)
    backup.write_bytes(b"tampered curriculum export")
    assert digest(backup) != expected_hash
