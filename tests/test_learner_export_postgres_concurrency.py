"""Opt-in concurrent learner export test against an explicitly disposable PostgreSQL DB.

Never run against production. The guard executes BEFORE importing CrownPath,
which initializes its database connection and app.
"""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlsplit

test_url = os.environ.get("CROWNPATH_TEST_POSTGRES_URL", "")
if not test_url.startswith(("postgresql://", "postgresql+psycopg://")):
    raise unittest.SkipTest("Explicit isolated PostgreSQL URL required")
# Refuse even an explicitly flagged database unless its name clearly denotes a
# disposable test database. Never log the connection URL (it may contain secrets).
db_name = urlsplit(test_url).path.lstrip("/").lower()
if not db_name or not any(tag in db_name for tag in ("disposable", "crownpath_test", "test_crownpath")):
    raise unittest.SkipTest("Database name must clearly identify an isolated test database")
if os.environ.get("CROWNPATH_DATABASE_URL") != test_url:
    raise unittest.SkipTest("Configured database URL must exactly match test URL")
if os.environ.get("CROWNPATH_ENV", "").lower() != "staging":
    raise unittest.SkipTest("Staging only")
if os.environ.get("CROWNPATH_TEST_DB_DISPOSABLE") != "YES":
    raise unittest.SkipTest("Explicit disposable test database confirmation required")
if os.environ.get("CROWNPATH_LEARNER_ACCESS_APPROVED", "").lower() != "true":
    raise unittest.SkipTest("Explicit staging learner access approval required")

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from crownpath.auth import create_user
from crownpath.database import init_db, session
from crownpath.main import app
from crownpath.models import AuditEvent, AuthToken, LearnerLessonStep, LearnerProgress, User


class PostgresLearnerExportConcurrencyTest(unittest.TestCase):
    def test_export_fails_closed_if_audit_commit_fails(self):
        from unittest.mock import patch
        from sqlalchemy.orm import Session
        init_db()
        email = f"synthetic-audit-failure-{uuid.uuid4().hex}@example.invalid"
        password = "Synthetic-Export-Only-2026!"
        user = create_user("Synthetic Audit Failure", email, password, "HOME_CARE")
        user_id = user["user_id"]
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                login = client.post("/api/auth/login", json={
                    "email": email, "password": password,
                })
                self.assertEqual(login.status_code, 200, login.text)
                with patch.object(Session, "commit", side_effect=RuntimeError("synthetic audit write failure")):
                    response = client.get("/api/learner/my-data-export")
                self.assertGreaterEqual(response.status_code, 500)
                self.assertNotIn("profile", response.text)
                self.assertNotIn("learning_progress", response.text)
                self.assertNotIn("lesson_steps", response.text)
            db = session()
            try:
                events = db.scalars(select(AuditEvent).where(
                    AuditEvent.user_id == user_id,
                    AuditEvent.action == "learner.self_export",
                )).all()
                self.assertEqual(events, [])
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuditEvent).where(AuditEvent.user_id == user_id))
                db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
                db.execute(delete(User).where(User.user_id == user_id))
                db.commit()
            finally:
                db.close()

    def test_expired_success_events_do_not_consume_hourly_quota(self):
        from datetime import datetime, timedelta, timezone
        init_db()
        email = f"synthetic-expiry-{uuid.uuid4().hex}@example.invalid"
        password = "Synthetic-Export-Only-2026!"
        user = create_user("Synthetic Expiry Learner", email, password, "HOME_CARE")
        user_id = user["user_id"]
        try:
            db = session()
            try:
                for _ in range(5):
                    db.add(AuditEvent(
                        user_id=user_id,
                        action="learner.self_export",
                        category="DATA_ACCESS",
                        resource_type="LEARNER_RECORDS",
                        resource_id=user_id,
                        result="SUCCESS",
                        reason="synthetic_expired_quota",
                        created_at=datetime.now(timezone.utc)-timedelta(hours=2),
                    ))
                db.commit()
            finally:
                db.close()
            with TestClient(app) as client:
                login = client.post("/api/auth/login", json={
                    "email": email, "password": password,
                })
                self.assertEqual(login.status_code, 200, login.text)
                response = client.get("/api/learner/my-data-export")
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["profile"]["user_id"], user_id)
        finally:
            db = session()
            try:
                db.execute(delete(AuditEvent).where(AuditEvent.user_id == user_id))
                db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
                db.execute(delete(User).where(User.user_id == user_id))
                db.commit()
            finally:
                db.close()

    def test_separate_learners_have_independent_quotas(self):
        init_db()
        users = []
        try:
            for _ in range(2):
                email = f"synthetic-independent-{uuid.uuid4().hex}@example.invalid"
                password = "Synthetic-Export-Only-2026!"
                user = create_user("Synthetic Independent Learner", email, password, "HOME_CARE")
                users.append(user["user_id"])
                with TestClient(app) as client:
                    login = client.post("/api/auth/login", json={
                        "email": email, "password": password,
                    })
                    self.assertEqual(login.status_code, 200, login.text)
                    for attempt in range(6):
                        response = client.get("/api/learner/my-data-export")
                        self.assertEqual(response.status_code, 200 if attempt < 5 else 429, response.text)
                        if attempt < 5:
                            self.assertEqual(response.json()["profile"]["user_id"], user["user_id"])
            db = session()
            try:
                for user_id in users:
                    events = db.scalars(select(AuditEvent).where(
                        AuditEvent.user_id == user_id,
                        AuditEvent.action == "learner.self_export",
                    )).all()
                    self.assertEqual(sum(e.result == "SUCCESS" for e in events), 5)
                    self.assertEqual(sum(e.result == "REJECTED" for e in events), 1)
            finally:
                db.close()
        finally:
            db = session()
            try:
                for user_id in users:
                    db.execute(delete(AuditEvent).where(AuditEvent.user_id == user_id))
                    db.execute(delete(LearnerLessonStep).where(LearnerLessonStep.user_id == user_id))
                    db.execute(delete(LearnerProgress).where(LearnerProgress.user_id == user_id))
                    db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
                    db.execute(delete(User).where(User.user_id == user_id))
                db.commit()
            finally:
                db.close()

    def test_ten_simultaneous_requests_only_five_succeed(self):
        init_db()
        email = f"synthetic-export-{uuid.uuid4().hex}@example.invalid"
        password = "Synthetic-Export-Only-2026!"
        user = create_user("Synthetic Export Race", email, password, "HOME_CARE")
        user_id = user["user_id"]
        try:
            with TestClient(app) as login_client:
                login_client.headers.update({"Origin": "http://testserver"})
                login = login_client.post("/api/auth/login", json={
                    "email": email, "password": password,
                })
                self.assertEqual(login.status_code, 200, login.text)
                cookie = login_client.cookies.get("crownpath_session")
                self.assertTrue(cookie)
            gate = Barrier(10)
            def request_export():
                with TestClient(app) as client:
                    client.cookies.set("crownpath_session", cookie)
                    gate.wait(timeout=20)
                    response = client.get("/api/learner/my-data-export")
                    return response.status_code, response.json()
            with ThreadPoolExecutor(max_workers=10) as pool:
                results = list(pool.map(lambda _: request_export(), range(10)))
            self.assertEqual(sum(status == 200 for status, _ in results), 5, results)
            self.assertEqual(sum(status == 429 for status, _ in results), 5, results)
            for status, payload in results:
                if status == 200:
                    self.assertEqual(payload["profile"]["user_id"], user_id)
                    self.assertNotIn("password_hash", str(payload))
                    self.assertNotIn("mfa_secret", str(payload))
                else:
                    self.assertEqual(status, 429)
                    self.assertNotIn("profile", payload)
                    self.assertNotIn("learning_progress", payload)
                    self.assertNotIn("lesson_steps", payload)
            db = session()
            try:
                events = db.scalars(select(AuditEvent).where(
                    AuditEvent.user_id == user_id,
                    AuditEvent.action == "learner.self_export",
                )).all()
                self.assertEqual(sum(e.result == "SUCCESS" for e in events), 5)
                self.assertEqual(sum(e.result == "REJECTED" for e in events), 5)
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuditEvent).where(AuditEvent.user_id == user_id))
                db.execute(delete(LearnerLessonStep).where(LearnerLessonStep.user_id == user_id))
                db.execute(delete(LearnerProgress).where(LearnerProgress.user_id == user_id))
                db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
                db.execute(delete(User).where(User.user_id == user_id))
                db.commit()
            finally:
                db.close()
