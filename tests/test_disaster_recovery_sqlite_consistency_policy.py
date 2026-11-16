"""Synthetic recovery database integrity checks before promotion.

Uses disposable SQLite files; production recovery must validate actual schema,
constraints, application behavior, and trusted external backup manifests.
"""
import sqlite3

import pytest


def _build(path):
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT NOT NULL)")
        db.execute("""CREATE TABLE progress (
            learner_id TEXT NOT NULL, lesson_id TEXT NOT NULL,
            completed INTEGER NOT NULL CHECK(completed IN (0, 1)),
            UNIQUE(learner_id, lesson_id),
            FOREIGN KEY(lesson_id) REFERENCES lessons(id))""")
        db.execute("INSERT INTO lessons VALUES ('lesson-1', 'Fictional lesson')")
        db.execute("INSERT INTO progress VALUES ('learner-1', 'lesson-1', 1)")


def _validate(path):
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=ON")
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise ValueError("Database integrity failure")
        if db.execute("PRAGMA foreign_key_check").fetchall():
            raise ValueError("Orphaned recovery record")
        duplicate = db.execute("""SELECT learner_id, lesson_id FROM progress
            GROUP BY learner_id, lesson_id HAVING COUNT(*) > 1""").fetchone()
        if duplicate:
            raise ValueError("Duplicate learner progress")
        invalid = db.execute(
            "SELECT 1 FROM progress WHERE completed NOT IN (0,1)"
        ).fetchone()
        if invalid:
            raise ValueError("Invalid progress state")
    return True


def test_consistent_recovery_database_is_eligible(tmp_path):
    path = tmp_path / "consistent.db"
    _build(path)
    assert _validate(path)


def test_orphaned_progress_is_rejected(tmp_path):
    path = tmp_path / "orphan.db"
    _build(path)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA foreign_keys=OFF")
        db.execute("UPDATE progress SET lesson_id='missing' WHERE learner_id='learner-1'")
    with pytest.raises(ValueError, match="Orphaned"):
        _validate(path)


def test_invalid_progress_state_is_rejected(tmp_path):
    path = tmp_path / "invalid.db"
    _build(path)
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA ignore_check_constraints=ON")
        db.execute("UPDATE progress SET completed=9")
    with pytest.raises(ValueError, match="Invalid progress|Database integrity failure"):
        _validate(path)


def test_truncated_database_is_rejected(tmp_path):
    path = tmp_path / "truncated.db"
    _build(path)
    data = path.read_bytes()
    path.write_bytes(data[:100])
    with pytest.raises((sqlite3.DatabaseError, ValueError)):
        _validate(path)
