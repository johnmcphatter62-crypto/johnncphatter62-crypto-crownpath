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
from crownpath.models import AuthToken, User


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
            db.execute(delete(AuthToken).where(AuthToken.user_id == self.user["user_id"]))
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
        payload = enabled.json()
        self.assertTrue(payload["mfa_enabled"])
        recovery_codes = payload.get("recovery_codes") or []
        self.assertEqual(len(recovery_codes), 8)
        self.assertEqual(len(set(recovery_codes)), 8)
        self.assertTrue(all(len(item) == 8 and item.isdigit() for item in recovery_codes))
        return secret, recovery_codes

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
        secret, _ = self.enable_mfa()
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

    def test_recovery_code_is_one_time_use_through_login(self):
        _, recovery_codes = self.enable_mfa()
        recovery_code = recovery_codes[0]
        db = session()
        try:
            rows = db.query(AuthToken).filter(AuthToken.user_id == self.user["user_id"], AuthToken.token_type == "MFA_RECOVERY").all()
            self.assertEqual(len(rows), 8)
            stored_hashes = {row.token_hash for row in rows}
            self.assertFalse(any(code in stored_hashes for code in recovery_codes))
        finally:
            db.close()

        self.client.cookies.clear()
        first_login = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(first_login.status_code, 200, first_login.text)
        first = self.client.post("/api/auth/mfa/verify", json={"challenge": first_login.json()["challenge"], "code": recovery_code})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["authenticated"])

        self.client.cookies.clear()
        second_login = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(second_login.status_code, 200, second_login.text)
        second = self.client.post("/api/auth/mfa/verify", json={"challenge": second_login.json()["challenge"], "code": recovery_code})
        self.assertEqual(second.status_code, 401, second.text)

    def test_repeated_invalid_mfa_codes_lock_account(self):
        self.enable_mfa()
        self.client.cookies.clear()
        login = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(login.status_code, 200, login.text)
        challenge = login.json()["challenge"]

        for attempt in range(1, 6):
            failed = self.client.post("/api/auth/mfa/verify", json={"challenge": challenge, "code": "000000"})
            expected_status = 423 if attempt == 5 else 401
            self.assertEqual(failed.status_code, expected_status, failed.text)

        db = session()
        try:
            row = db.get(User, self.user["user_id"])
            self.assertEqual(row.failed_login_attempts, 0)
            self.assertIsNotNone(row.locked_until)
        finally:
            db.close()

        locked_login = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(locked_login.status_code, 423, locked_login.text)


if __name__ == "__main__":
    unittest.main()
