import os
import unittest
import uuid
from unittest.mock import patch

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-owner-access-tests-2026")

from fastapi.testclient import TestClient
from sqlalchemy import delete

from crownpath.auth import create_user
from crownpath.database import session
from crownpath.main import app
from crownpath.models import AuthToken, User


class OwnerOnlyAccessTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.password = "CrownPath-Owner-Test-2026!"
        self.suffix = uuid.uuid4().hex[:12]
        self.user_ids = []
        self.flags = {
            "CROWNPATH_LEARNER_ACCESS_APPROVED": "false",
            "CROWNPATH_LEARNER_ENROLLMENT_APPROVED": "false",
            "CROWNPATH_INSTRUCTOR_ACCESS_APPROVED": "false",
        }

    def tearDown(self):
        self.client.cookies.clear()
        db = session()
        try:
            db.execute(delete(AuthToken).where(AuthToken.user_id.in_(self.user_ids)))
            db.execute(delete(User).where(User.user_id.in_(self.user_ids)))
            db.commit()
        finally:
            db.close()

    def add_account(self, role):
        email = f"owner-only-{role.lower()}-{self.suffix}@example.com"
        user = create_user("Access Test", email, self.password, "HOME_CARE")
        self.user_ids.append(user["user_id"])
        if role != "HOME_CARE":
            db = session()
            try:
                row = db.get(User, user["user_id"])
                row.role = role
                row.track = role
                db.commit()
            finally:
                db.close()
        return email

    def login(self, email):
        return self.client.post("/api/auth/login", json={"email": email, "password": self.password})

    def test_owner_only_blocks_new_accounts_and_existing_non_owner_sign_in(self):
        learner_email = self.add_account("HOME_CARE")
        instructor_email = self.add_account("INSTRUCTOR")
        owner_email = self.add_account("OWNER")
        with patch.dict(os.environ, self.flags):
            status = self.client.get("/api/auth/enrollment/status")
            self.assertEqual(status.status_code, 200)
            self.assertFalse(status.json()["enabled"])
            registration = self.client.post("/api/auth/register", json={
                "name": "New Learner",
                "email": f"closed-{self.suffix}@example.com",
                "password": self.password,
                "role": "BARBER",
            })
            self.assertEqual(registration.status_code, 403)
            self.assertIsNone(self.client.cookies.get("crownpath_session"))
            self.assertEqual(self.login(learner_email).status_code, 403)
            self.assertEqual(self.login(instructor_email).status_code, 403)
            self.assertIsNone(self.client.cookies.get("crownpath_session"))
            owner_login = self.login(owner_email)
            self.assertEqual(owner_login.status_code, 200, owner_login.text)
            self.assertEqual(self.client.get("/api/auth/me").json()["role"], "OWNER")

    def test_existing_learner_session_loses_access_when_gate_closes(self):
        learner_email = self.add_account("BARBER")
        with patch.dict(os.environ, {**self.flags, "CROWNPATH_LEARNER_ACCESS_APPROVED": "true"}):
            self.assertEqual(self.login(learner_email).status_code, 200)
            self.assertEqual(self.client.get("/api/learner/dashboard").status_code, 200)
        with patch.dict(os.environ, self.flags):
            self.assertEqual(self.client.get("/api/auth/me").status_code, 403)
            self.assertEqual(self.client.get("/api/learner/dashboard").status_code, 403)

    def test_enrollment_requires_separate_learner_access_and_enrollment_flags(self):
        email = f"enrolled-{self.suffix}@example.com"
        payload = {"name": "New Learner", "email": email, "password": self.password, "role": "COSMETOLOGY_PRO"}
        with patch.dict(os.environ, {**self.flags, "CROWNPATH_LEARNER_ENROLLMENT_APPROVED": "true"}):
            self.assertEqual(self.client.post("/api/auth/register", json=payload).status_code, 403)
        with patch.dict(os.environ, {**self.flags, "CROWNPATH_LEARNER_ACCESS_APPROVED": "true"}):
            self.assertEqual(self.client.post("/api/auth/register", json=payload).status_code, 403)
        with patch.dict(os.environ, {**self.flags, "CROWNPATH_LEARNER_ACCESS_APPROVED": "true", "CROWNPATH_LEARNER_ENROLLMENT_APPROVED": "true"}):
            created = self.client.post("/api/auth/register", json=payload)
            self.assertEqual(created.status_code, 200, created.text)
            self.user_ids.append(created.json()["user"]["user_id"])
            self.assertEqual(self.client.get("/api/auth/me").status_code, 200)
