"""Disaster recovery safety gate: classroom data restores without live sessions.

Synthetic standalone SQLite source/restore databases; no production backups.
"""
import shutil
import sqlite3


def _init(db_path):
    with sqlite3.connect(db_path) as db:
        db.executescript("""
            CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT NOT NULL);
            CREATE TABLE progress (learner_id TEXT NOT NULL, lesson_id TEXT NOT NULL,
                completed INTEGER NOT NULL);
            CREATE TABLE sessions (token TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0);
        """)
        db.execute("INSERT INTO lessons VALUES (?, ?)", ("fictional-lesson", "Synthetic lesson"))
        db.execute("INSERT INTO progress VALUES (?, ?, ?)",
                   ("fictional-learner", "fictional-lesson", 1))
        db.execute("INSERT INTO sessions VALUES (?, ?, ?)",
                   ("fictional-old-session", "fictional-learner", 0))


def _restore_without_sessions(backup_path, recovered_path):
    # Copy only the curriculum/progress tables into a new, empty recovery DB.
    # Session credentials must not be carried over as active credentials.
    with sqlite3.connect(backup_path) as src, sqlite3.connect(recovered_path) as dst:
        dst.executescript("""
            CREATE TABLE lessons (id TEXT PRIMARY KEY, title TEXT NOT NULL);
            CREATE TABLE progress (learner_id TEXT NOT NULL, lesson_id TEXT NOT NULL,
                completed INTEGER NOT NULL);
            CREATE TABLE sessions (token TEXT PRIMARY KEY, learner_id TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0);
        """)
        dst.executemany("INSERT INTO lessons VALUES (?, ?)",
                        src.execute("SELECT id, title FROM lessons").fetchall())
        dst.executemany("INSERT INTO progress VALUES (?, ?, ?)",
                        src.execute("SELECT learner_id, lesson_id, completed FROM progress").fetchall())


def test_recovery_preserves_classroom_but_never_revives_old_session(tmp_path):
    source = tmp_path / "source.db"
    backup = tmp_path / "backup.db"
    restored = tmp_path / "restored.db"
    _init(source)
    shutil.copyfile(source, backup)
    _restore_without_sessions(backup, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT id, title FROM lessons").fetchall() == [
            ("fictional-lesson", "Synthetic lesson")]
        assert db.execute("SELECT learner_id, lesson_id, completed FROM progress").fetchall() == [
            ("fictional-learner", "fictional-lesson", 1)]
        assert db.execute("SELECT * FROM sessions").fetchall() == []
        assert db.execute(
            "SELECT 1 FROM sessions WHERE token = ? AND revoked = 0",
            ("fictional-old-session",)
        ).fetchone() is None
