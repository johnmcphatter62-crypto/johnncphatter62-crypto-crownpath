import os
import unittest
import uuid

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-instructor-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import delete

from crownpath.auth import create_user
from crownpath.database import init_db, session
from crownpath.main import app
from crownpath.models import AuthToken, InstructorRequest, User


class InstructorRequestIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.client = TestClient(app)
        suffix = uuid.uuid4().hex[:10]
        self.learner_email = f"instructor-applicant-{suffix}@example.com"
        self.owner_email = f"owner-reviewer-{suffix}@example.com"
        self.password = "CrownPath-Workflow-2026!"
        self.learner = create_user("Instructor Applicant", self.learner_email, self.password, "HOME_CARE")
        self.owner = create_user("Owner Reviewer", self.owner_email, self.password, "HOME_CARE")
        db = session()
        try:
            owner_row = db.get(User, self.owner["user_id"])
            owner_row.role = "OWNER"
            owner_row.track = "OWNER"
            owner_row.active = True
            db.commit()
        finally:
            db.close()

    def tearDown(self):
        self.client.cookies.clear()
        user_ids = [self.learner["user_id"], self.owner["user_id"]]
        db = session()
        try:
            db.execute(delete(InstructorRequest).where(InstructorRequest.user_id.in_(user_ids)))
            db.execute(delete(AuthToken).where(AuthToken.user_id.in_(user_ids)))
            db.execute(delete(User).where(User.user_id.in_(user_ids)))
            db.commit()
        finally:
            db.close()

    def login(self, email):
        self.client.cookies.clear()
        response = self.client.post("/api/auth/login", json={"email": email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        return response

    def submit_request(self, statement="I am qualified and would like to teach CrownPath learners."):
        self.login(self.learner_email)
        response = self.client.post("/api/instructor-requests", json={"statement": statement})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["request"]

    def test_learner_can_submit_and_duplicate_pending_is_blocked(self):
        request = self.submit_request()
        self.assertEqual(request["status"], "PENDING")
        duplicate = self.client.post("/api/instructor-requests", json={"statement": "This is another Instructor request while one is pending."})
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        history = self.client.get("/api/instructor-requests/me")
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["requests"][0]["request_id"], request["request_id"])

    def test_owner_can_approve_with_review_note_and_role_changes(self):
        request = self.submit_request()
        self.login(self.owner_email)
        note = "Qualifications reviewed. Approved for CrownPath Instructor access."
        review = self.client.patch(f"/api/owner/instructor-requests/{request['request_id']}", json={"decision": "APPROVE", "note": note})
        self.assertEqual(review.status_code, 200, review.text)
        payload = review.json()
        self.assertEqual(payload["request"]["status"], "APPROVED")
        self.assertEqual(payload["request"]["review_note"], note)
        self.assertEqual(payload["applicant"]["role"], "INSTRUCTOR")
        self.assertTrue(payload["applicant"]["active"])
        second_review = self.client.patch(f"/api/owner/instructor-requests/{request['request_id']}", json={"decision": "DENY"})
        self.assertEqual(second_review.status_code, 409, second_review.text)

    def test_owner_can_deny_and_learner_role_remains_unchanged(self):
        request = self.submit_request()
        self.login(self.owner_email)
        note = "Additional qualifications are required before Instructor approval."
        review = self.client.patch(f"/api/owner/instructor-requests/{request['request_id']}", json={"decision": "DENY", "note": note})
        self.assertEqual(review.status_code, 200, review.text)
        self.assertEqual(review.json()["request"]["status"], "DENIED")
        self.assertEqual(review.json()["request"]["review_note"], note)
        db = session()
        try:
            applicant = db.get(User, self.learner["user_id"])
            self.assertEqual(applicant.role, "HOME_CARE")
        finally:
            db.close()

    def test_learner_cannot_access_owner_review_endpoints(self):
        request = self.submit_request()
        listing = self.client.get("/api/owner/instructor-requests")
        self.assertEqual(listing.status_code, 403, listing.text)
        review = self.client.patch(f"/api/owner/instructor-requests/{request['request_id']}", json={"decision": "APPROVE"})
        self.assertEqual(review.status_code, 403, review.text)

    def test_owner_and_instructor_do_not_need_instructor_request(self):
        self.login(self.owner_email)
        owner_request = self.client.post("/api/instructor-requests", json={"statement": "Owner should not submit an Instructor request."})
        self.assertEqual(owner_request.status_code, 400, owner_request.text)
        db = session()
        try:
            learner = db.get(User, self.learner["user_id"])
            learner.role = "INSTRUCTOR"
            learner.track = "INSTRUCTOR"
            db.commit()
        finally:
            db.close()
        self.login(self.learner_email)
        instructor_request = self.client.post("/api/instructor-requests", json={"statement": "Instructor should not submit another Instructor request."})
        self.assertEqual(instructor_request.status_code, 400, instructor_request.text)


if __name__ == "__main__":
    unittest.main()
