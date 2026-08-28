import os
import unittest
import uuid

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-learner-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import delete

from crownpath.auth import create_user, set_user_role
from crownpath.database import init_db, session
from crownpath.main import app
from crownpath.models import LearnerProgress, User


class LearnerProgressIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        suffix = uuid.uuid4().hex[:10]
        self.email = f"learner-{suffix}@example.invalid"
        self.password = "CrownPath-Learner-2026!"
        self.user = create_user("Learner Test", self.email, self.password, "HOME_CARE")
        response = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        db = session()
        try:
            db.execute(delete(LearnerProgress).where(LearnerProgress.user_id == self.user["user_id"]))
            db.execute(delete(User).where(User.user_id == self.user["user_id"]))
            db.commit()
        finally:
            db.close()

    def test_dashboard_open_complete_and_saved_progress(self):
        dashboard = self.client.get("/api/learner/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        payload = dashboard.json()
        self.assertEqual(payload["role"], "HOME_CARE")
        self.assertEqual(payload["overall_progress"], 0)
        lesson_id = payload["modules"][0]["lesson_id"]

        opened = self.client.post(f"/api/learner/lessons/{lesson_id}/open")
        self.assertEqual(opened.status_code, 200)
        self.assertEqual(opened.json()["lesson"]["status"], "IN_PROGRESS")
        self.assertGreaterEqual(opened.json()["lesson"]["progress"], 25)

        refreshed = self.client.get("/api/learner/dashboard").json()
        first = next(item for item in refreshed["modules"] if item["lesson_id"] == lesson_id)
        self.assertEqual(first["status"], "IN_PROGRESS")
        self.assertGreaterEqual(first["progress"], 25)
        self.assertGreater(refreshed["overall_progress"], 0)

        completed = self.client.post(f"/api/learner/lessons/{lesson_id}/complete")
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["lesson"]["status"], "COMPLETED")
        self.assertEqual(completed.json()["lesson"]["progress"], 100)

        final_dashboard = self.client.get("/api/learner/dashboard").json()
        first = next(item for item in final_dashboard["modules"] if item["lesson_id"] == lesson_id)
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(first["progress"], 100)

    def test_invalid_lesson_is_rejected(self):
        response = self.client.post("/api/learner/lessons/not-a-real-lesson/open")
        self.assertEqual(response.status_code, 404)

    def test_instructor_cannot_use_learner_dashboard(self):
        set_user_role(self.user["user_id"], "INSTRUCTOR", True)
        response = self.client.get("/api/learner/dashboard")
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
