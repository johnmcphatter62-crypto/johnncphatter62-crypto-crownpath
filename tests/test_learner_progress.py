import os
import unittest
import uuid

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-learner-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import delete

from crownpath.auth import create_user, set_user_role
from crownpath.database import init_db, session
from crownpath.lesson_content import get_canonical_lesson_content, get_lesson_content
from crownpath.main import app, learner_catalog
from crownpath.models import AuthToken, LearnerLessonStep, LearnerProgress, User


FORBIDDEN_LEARNER_KEYS = {
    "answer_index",
    "rationale",
    "instructor_notes",
    "answer_key",
    "instructor_answer_key",
    "correct_answer",
}


def collect_keys(value):
    keys = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(key)
            keys.update(collect_keys(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            keys.update(collect_keys(item))
    return keys


class LearnerProgressIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        suffix = uuid.uuid4().hex[:10]
        self.email = f"learner-{suffix}@example.com"
        self.password = "CrownPath-Learner-2026!"
        self.user = create_user("Learner Test", self.email, self.password, "HOME_CARE")
        response = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)

    def tearDown(self):
        db = session()
        try:
            db.execute(delete(LearnerLessonStep).where(LearnerLessonStep.user_id == self.user["user_id"]))
            db.execute(delete(LearnerProgress).where(LearnerProgress.user_id == self.user["user_id"]))
            db.execute(delete(AuthToken).where(AuthToken.user_id == self.user["user_id"]))
            db.execute(delete(User).where(User.user_id == self.user["user_id"]))
            db.commit()
        finally:
            db.close()
        self.client.cookies.clear()

    def login_as_role(self, role):
        set_user_role(self.user["user_id"], role, True)
        self.client.cookies.clear()
        response = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)

    def assert_learner_safe(self, content):
        self.assertTrue(content.get("summary"))
        self.assertTrue(content.get("steps"))
        self.assertFalse(FORBIDDEN_LEARNER_KEYS.intersection(collect_keys(content)))

    def test_step_progress_persists_and_completed_lesson_can_be_reviewed(self):
        dashboard = self.client.get("/api/learner/dashboard")
        self.assertEqual(dashboard.status_code, 200, dashboard.text)
        payload = dashboard.json()
        self.assertEqual(payload["role"], "HOME_CARE")
        self.assertEqual(payload["overall_progress"], 0)
        lesson_id = payload["modules"][0]["lesson_id"]

        opened = self.client.post(f"/api/learner/lessons/{lesson_id}/open")
        self.assertEqual(opened.status_code, 200, opened.text)
        lesson = opened.json()["lesson"]
        self.assertEqual(lesson["status"], "IN_PROGRESS")
        self.assertEqual(lesson["progress"], 0)
        self.assertEqual(lesson["completed_steps"], [])
        self.assertGreater(lesson["total_steps"], 0)
        self.assertTrue(lesson["content"]["summary"])
        self.assertTrue(lesson["content"]["objectives"])
        self.assertTrue(lesson["content"]["steps"])
        self.assertTrue(lesson["content"]["safety_note"])
        self.assert_learner_safe(lesson["content"])

        first_step = self.client.post(f"/api/learner/lessons/{lesson_id}/steps/1/complete")
        self.assertEqual(first_step.status_code, 200, first_step.text)
        step_payload = first_step.json()["lesson"]
        self.assertIn(1, step_payload["completed_steps"])
        self.assertGreater(step_payload["progress"], 0)
        self.assertLessEqual(step_payload["progress"], 100)

        duplicate = self.client.post(f"/api/learner/lessons/{lesson_id}/steps/1/complete")
        self.assertEqual(duplicate.status_code, 200, duplicate.text)
        self.assertEqual(duplicate.json()["lesson"]["completed_steps"].count(1), 1)

        reopened = self.client.post(f"/api/learner/lessons/{lesson_id}/open")
        self.assertEqual(reopened.status_code, 200, reopened.text)
        self.assertIn(1, reopened.json()["lesson"]["completed_steps"])
        self.assertEqual(reopened.json()["lesson"]["progress"], step_payload["progress"])

        total_steps = reopened.json()["lesson"]["total_steps"]
        for step_index in range(2, total_steps + 1):
            response = self.client.post(f"/api/learner/lessons/{lesson_id}/steps/{step_index}/complete")
            self.assertEqual(response.status_code, 200, response.text)

        completed_review = self.client.post(f"/api/learner/lessons/{lesson_id}/open")
        self.assertEqual(completed_review.status_code, 200, completed_review.text)
        completed_lesson = completed_review.json()["lesson"]
        self.assertEqual(completed_lesson["status"], "COMPLETED")
        self.assertEqual(completed_lesson["progress"], 100)
        self.assertEqual(len(completed_lesson["completed_steps"]), total_steps)
        self.assertTrue(completed_lesson["content"]["steps"])

        final_dashboard = self.client.get("/api/learner/dashboard").json()
        first = next(item for item in final_dashboard["modules"] if item["lesson_id"] == lesson_id)
        self.assertEqual(first["status"], "COMPLETED")
        self.assertEqual(first["progress"], 100)

    def test_complete_lesson_marks_all_steps_complete(self):
        dashboard = self.client.get("/api/learner/dashboard").json()
        lesson_id = dashboard["modules"][1]["lesson_id"]
        completed = self.client.post(f"/api/learner/lessons/{lesson_id}/complete")
        self.assertEqual(completed.status_code, 200, completed.text)
        lesson = completed.json()["lesson"]
        self.assertEqual(lesson["status"], "COMPLETED")
        self.assertEqual(lesson["progress"], 100)
        self.assertEqual(len(lesson["completed_steps"]), lesson["total_steps"])

    def test_all_catalog_lessons_resolve_and_are_learner_safe(self):
        for role in ("HOME_CARE", "BARBER", "COSMETOLOGY_PRO"):
            for lesson_id, _title in learner_catalog(role):
                with self.subTest(role=role, lesson_id=lesson_id):
                    canonical = get_canonical_lesson_content(lesson_id)
                    learner = get_lesson_content(lesson_id)
                    self.assertIsNotNone(canonical)
                    self.assertIsNotNone(learner)
                    self.assertTrue(canonical.get("steps"))
                    self.assertEqual(canonical["steps"], learner["steps"])
                    self.assert_learner_safe(learner)

    def test_canonical_quiz_keys_remain_server_side_but_not_in_learner_content(self):
        lesson_ids = [
            "home-care-foundations",
            "barber-hair-scalp",
            "barber-scalp-camera-assessment",
            "cosmetology-foundations",
            "cosmetology-hair-scalp",
            "cosmetology-scalp-camera-assessment",
            "cosmetology-chemical-safety",
            "cosmetology-hair-replacement",
            "cosmetology-makeup-artistry",
            "cosmetology-nail-care",
            "wellness-client-experience",
            "avatar-bot-builder-foundations",
        ]
        for lesson_id in lesson_ids:
            with self.subTest(lesson_id=lesson_id):
                canonical = get_canonical_lesson_content(lesson_id)
                learner = get_lesson_content(lesson_id)
                self.assertIsNotNone(canonical)
                self.assertIsNotNone(learner)
                if canonical.get("knowledge_check"):
                    self.assertIn("answer_index", canonical["knowledge_check"][0])
                    self.assertNotIn("answer_index", learner["knowledge_check"][0])
                    self.assertNotIn("rationale", learner["knowledge_check"][0])
                    self.assertTrue(learner["knowledge_check"][0].get("question"))
                    self.assertTrue(learner["knowledge_check"][0].get("options"))

    def test_barber_and_cosmetology_can_open_expanded_lessons_and_cross_track_is_blocked(self):
        self.login_as_role("BARBER")
        barber = self.client.post("/api/learner/lessons/barber-scalp-camera-assessment/open")
        self.assertEqual(barber.status_code, 200, barber.text)
        self.assert_learner_safe(barber.json()["lesson"]["content"])
        wrong_cos = self.client.post("/api/learner/lessons/cosmetology-makeup-artistry/open")
        self.assertEqual(wrong_cos.status_code, 404)

        self.login_as_role("COSMETOLOGY_PRO")
        for lesson_id in ("cosmetology-hair-scalp", "cosmetology-scalp-camera-assessment", "cosmetology-makeup-artistry", "cosmetology-nail-care"):
            opened = self.client.post(f"/api/learner/lessons/{lesson_id}/open")
            self.assertEqual(opened.status_code, 200, opened.text)
            self.assert_learner_safe(opened.json()["lesson"]["content"])
        wrong_barber = self.client.post("/api/learner/lessons/barber-foundations/open")
        self.assertEqual(wrong_barber.status_code, 404)

    def test_four_step_expanded_lesson_reaches_100_percent(self):
        self.login_as_role("BARBER")
        lesson_id = "barber-scalp-camera-assessment"
        opened = self.client.post(f"/api/learner/lessons/{lesson_id}/open")
        self.assertEqual(opened.status_code, 200, opened.text)
        self.assertEqual(opened.json()["lesson"]["total_steps"], 4)
        for step_index in range(1, 5):
            response = self.client.post(f"/api/learner/lessons/{lesson_id}/steps/{step_index}/complete")
            self.assertEqual(response.status_code, 200, response.text)
        final = self.client.post(f"/api/learner/lessons/{lesson_id}/open").json()["lesson"]
        self.assertEqual(final["status"], "COMPLETED")
        self.assertEqual(final["progress"], 100)
        self.assertEqual(final["completed_steps"], [1, 2, 3, 4])

    def test_invalid_lesson_and_step_are_rejected(self):
        response = self.client.post("/api/learner/lessons/not-a-real-lesson/open")
        self.assertEqual(response.status_code, 404)
        dashboard = self.client.get("/api/learner/dashboard").json()
        lesson_id = dashboard["modules"][0]["lesson_id"]
        invalid_step = self.client.post(f"/api/learner/lessons/{lesson_id}/steps/999/complete")
        self.assertEqual(invalid_step.status_code, 404)

    def test_wrong_path_lesson_is_rejected(self):
        response = self.client.post("/api/learner/lessons/barber-foundations/open")
        self.assertEqual(response.status_code, 404)

    def test_instructor_cannot_use_learner_endpoints(self):
        set_user_role(self.user["user_id"], "INSTRUCTOR", True)
        dashboard = self.client.get("/api/learner/dashboard")
        self.assertEqual(dashboard.status_code, 403)
        step = self.client.post("/api/learner/lessons/home-care-foundations/steps/1/complete")
        self.assertEqual(step.status_code, 403)


if __name__ == "__main__":
    unittest.main()
