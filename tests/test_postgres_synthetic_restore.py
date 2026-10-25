"""Synthetic PostgreSQL dump/restore exercise. CI-only, no production access."""
import os
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from crownpath.database import init_db, session
from crownpath.models import LearnerProgress, User

SOURCE = os.environ.get("CROWNPATH_TEST_POSTGRES_URL", "")
DATABASE = os.environ.get("CROWNPATH_DATABASE_URL", "")
parsed = urlparse(SOURCE)
if not (
    SOURCE.startswith(("postgresql://", "postgresql+psycopg://"))
    and SOURCE == DATABASE
    and os.environ.get("CROWNPATH_ENV") == "staging"
    and os.environ.get("CROWNPATH_TEST_DB_DISPOSABLE") == "YES"
    and parsed.hostname in ("localhost", "127.0.0.1", "::1")
    and "disposable" in (parsed.path or "").lower()
):
    raise unittest.SkipTest("Disposable localhost PostgreSQL test configuration required")


def pg_env():
    env = os.environ.copy()
    env["PGPASSWORD"] = parsed.password or ""
    return env


def run_pg(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, env=pg_env())


class PostgresSyntheticRestoreTest(unittest.TestCase):
    def test_dump_and_restore_into_separate_database(self):
        init_db()
        marker = uuid.uuid4().hex
        uid = "restore-" + marker
        lesson = "restore-lesson-" + marker
        restore_name = "crownpath_restore_disposable_" + marker[:12]
        admin_url = SOURCE.rsplit("/", 1)[0] + "/postgres"
        restore_url = SOURCE.rsplit("/", 1)[0] + "/" + restore_name
        source_session = session()
        restore_engine = None
        created = False
        try:
            source_session.add(User(
                user_id=uid, name="Synthetic Restore Learner",
                email=f"restore-{marker}@example.com",
                password_hash="synthetic-hash-not-a-real-credential",
                role="HOME_CARE", track="HOME_CARE", active=True,
            ))
            source_session.add(LearnerProgress(
                progress_id="progress-" + marker, user_id=uid,
                lesson_id=lesson, status="IN_PROGRESS", progress_percent=40,
            ))
            source_session.commit()
            with tempfile.TemporaryDirectory(prefix="crownpath-restore-") as tmp:
                dump = str(Path(tmp) / "synthetic.dump")
                # Credentials are provided only through PGPASSWORD, not CLI arguments.
                run_pg("pg_dump", "-h", parsed.hostname, "-p", str(parsed.port or 5432),
                       "-U", parsed.username, "-Fc", "-f", dump, parsed.path.lstrip("/"))
                run_pg("psql", "-h", parsed.hostname, "-p", str(parsed.port or 5432),
                       "-U", parsed.username, "-d", "postgres", "-v", "ON_ERROR_STOP=1",
                       "-c", f"CREATE DATABASE {restore_name}")
                created = True
                run_pg("pg_restore", "-h", parsed.hostname, "-p", str(parsed.port or 5432),
                       "-U", parsed.username, "-d", restore_name, "--exit-on-error", dump)
                restore_engine = create_engine(restore_url)
                with Session(restore_engine) as restored:
                    user = restored.scalar(select(User).where(User.user_id == uid))
                    progress = restored.scalar(select(LearnerProgress).where(
                        LearnerProgress.user_id == uid, LearnerProgress.lesson_id == lesson))
                    self.assertIsNotNone(user)
                    self.assertEqual(user.email, f"restore-{marker}@example.com")
                    self.assertIsNotNone(progress)
                    self.assertEqual(progress.progress_percent, 40)
                    self.assertEqual(progress.status, "IN_PROGRESS")
                    self.assertEqual(restored.scalar(text(
                        "SELECT count(*) FROM learner_progress WHERE user_id = :uid"
                    ).bindparams(uid=uid)), 1)
        finally:
            source_session.rollback()
            source_session.execute(
                text("DELETE FROM learner_progress WHERE user_id = :uid"), {"uid": uid})
            source_session.execute(text("DELETE FROM users WHERE user_id = :uid"), {"uid": uid})
            source_session.commit()
            source_session.close()
            if restore_engine is not None:
                restore_engine.dispose()
            if created:
                run_pg("psql", "-h", parsed.hostname, "-p", str(parsed.port or 5432),
                       "-U", parsed.username, "-d", "postgres", "-v", "ON_ERROR_STOP=1",
                       "-c", f"DROP DATABASE {restore_name} WITH (FORCE)")
