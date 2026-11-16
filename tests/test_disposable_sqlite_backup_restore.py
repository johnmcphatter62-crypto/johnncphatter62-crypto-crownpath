"""Disposable SQLite backup/restore proof: synthetic records only, never production."""
import sqlite3

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, LearnerProgress


def test_synthetic_backup_restores_users_and_progress(tmp_path):
    source_path = tmp_path / "synthetic_source.db"
    backup_path = tmp_path / "synthetic_backup.db"
    restored_path = tmp_path / "synthetic_restored.db"
    source_engine = create_engine(f"sqlite:///{source_path}")
    restored_engine = None
    try:
        Base.metadata.create_all(source_engine)
        with Session(source_engine) as db:
            db.add(User(
                user_id="synthetic-learner", name="Synthetic Learner",
                email="synthetic-backup@example.invalid",
                password_hash="synthetic-test-hash-not-a-credential",
                role="COSMETOLOGY_PRO", active=True,
            ))
            db.add(LearnerProgress(
                progress_id="synthetic-progress",
                user_id="synthetic-learner",
                lesson_id="synthetic-lesson",
                status="IN_PROGRESS", progress_percent=40,
            ))
            db.commit()

        # SQLite's online backup API creates a consistent snapshot. No real
        # CrownPath database, secrets, or external service is ever opened.
        with sqlite3.connect(source_path) as src, sqlite3.connect(backup_path) as dest:
            src.backup(dest)
        with sqlite3.connect(backup_path) as src, sqlite3.connect(restored_path) as dest:
            src.backup(dest)
        with sqlite3.connect(restored_path) as restored:
            assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert restored.execute("PRAGMA foreign_key_check").fetchall() == []

        restored_engine = create_engine(f"sqlite:///{restored_path}")
        with Session(restored_engine) as db:
            user = db.get(User, "synthetic-learner")
            progress = db.get(LearnerProgress, "synthetic-progress")
            assert user is not None
            assert user.email == "synthetic-backup@example.invalid"
            assert progress is not None
            assert progress.user_id == user.user_id
            assert progress.lesson_id == "synthetic-lesson"
            assert progress.progress_percent == 40
            assert db.scalar(select(User).where(User.email == user.email)) is not None
    finally:
        source_engine.dispose()
        if restored_engine is not None:
            restored_engine.dispose()
