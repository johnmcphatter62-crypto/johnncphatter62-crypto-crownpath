import os
import unittest
import uuid

import pyotp

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-mfa-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import delete

from crownpath.auth import create_user
from crownpath.database import init_db, session
from crownpath.main import app
from crownpath.models import User


class MfaIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.client = TestClient(app)
        suffix = uuid.uuid4().hex[:10]
        self.email = f"mfa-user-{suffix}@example.com"
        self.password = "CrownPath-MFA-2026!"
        self.user = create_user("MFA Test User", self.email, self.password, "HOME_CARE")

    def tearDown(self):
        self.client.cookies.clear()
        db = session()
        try:
            db.execute(delete(User).where(User.user_id == self.user["user_id"]))
            db.commit()
        finally:
            db.close()

    def login_without_mfa(self):
        response = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["authenticated"])
        return response

    def enable_mfa(self):
        self.login_without_mfa()
        setup = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(setup.status_code, 200, setup.text)
        secret = setup.json()["secret"]
        self.assertTrue(secret)
        self.assertIn("otpauth://totp/", setup.json()["provisioning_uri"])
        code = pyotp.TOTP(secret).now()
        enabled = self.client.post("/api/auth/mfa/enable", json={"code": code})
        self.assertEqual(enabled.status_code, 200, enabled.text)
        self.assertTrue(enabled.json()["mfa_enabled"])
        return secret

    def test_mfa_setup_requires_authentication(self):
        response = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(response.status_code, 401, response.text)

    def test_invalid_enable_code_does_not_enable_mfa(self):
        self.login_without_mfa()
        setup = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(setup.status_code, 200, setup.text)
        response = self.client.post("/api/auth/mfa/enable", json={"code": "000000"})
        self.assertEqual(response.status_code, 400, response.text)
        db = session()
        try:
            row = db.get(User, self.user["user_id"])
            self.assertFalse(row.mfa_enabled)
        finally:
            db.close()

    def test_enabled_mfa_requires_challenge_and_valid_code(self):
        secret = self.enable_mfa()
        self.client.cookies.clear()
        login = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(login.status_code, 200, login.text)
        payload = login.json()
        self.assertFalse(payload["authenticated"])
        self.assertTrue(payload["mfa_required"])
        self.assertTrue(payload["challenge"])
        self.assertNotIn("user_id", payload)

        invalid = self.client.post("/api/auth/mfa/verify", json={"challenge": payload["challenge"], "code": "000000"})
        self.assertEqual(invalid.status_code, 401, invalid.text)
        self.assertIsNone(self.client.cookies.get("crownpath_session"))

        valid_code = pyotp.TOTP(secret).now()
        verified = self.client.post("/api/auth/mfa/verify", json={"challenge": payload["challenge"], "code": valid_code})
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertTrue(verified.json()["authenticated"])
        self.assertTrue(verified.json()["user"]["mfa_enabled"])
        self.assertIsNotNone(self.client.cookies.get("crownpath_session"))

        me = self.client.get("/api/auth/me")
        self.assertEqual(me.status_code, 200, me.text)
        self.assertEqual(me.json()["email"], self.email)

    def test_invalid_mfa_challenge_is_rejected(self):
        self.enable_mfa()
        self.client.cookies.clear()
        response = self.client.post("/api/auth/mfa/verify", json={"challenge": "x" * 32, "code": "123456"})
        self.assertEqual(response.status_code, 401, response.text)


if __name__ == "__main__":
    unittest.main()
