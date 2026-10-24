import hashlib
import os
import unittest
import uuid

import pyotp

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-mfa-tests-123456789")

from fastapi.testclient import TestClient
from sqlalchemy import delete

os.environ.setdefault("CROWNPATH_LEARNER_ACCESS_APPROVED", "true")
os.environ.setdefault("CROWNPATH_LEARNER_ENROLLMENT_APPROVED", "true")
os.environ.setdefault("CROWNPATH_INSTRUCTOR_ACCESS_APPROVED", "true")

from crownpath.auth import _hash_mfa_recovery_code, consume_mfa_recovery_code, create_user
from crownpath.database import init_db, session
from crownpath.main import app
from crownpath.models import AuthToken, User


class MfaIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        self.client = TestClient(app)
        self.client.headers.update({'Origin': 'http://testserver'})
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

    def test_owner_activation_rejects_existing_mfa_account_without_mutation(self):
        from unittest.mock import patch
        from crownpath.auth import create_owner, get_user_by_id

        self.enable_mfa()
        before = get_user_by_id(self.user["user_id"])
        with patch.dict(os.environ, {
            "CROWNPATH_OWNER_EMAIL": self.email,
            "CROWNPATH_OWNER_ACTIVATION_CODE": "synthetic-activation-code",
        }):
            with self.assertRaisesRegex(ValueError, "separately verified Owner provisioning"):
                create_owner("Changed Owner", self.email, "Replacement-Password-2026!", "synthetic-activation-code")

        after = get_user_by_id(self.user["user_id"])
        self.assertEqual(after["role"], before["role"])
        self.assertEqual(after["password_hash"], before["password_hash"])
        self.assertEqual(after["mfa_secret"], before["mfa_secret"])
        self.assertTrue(after["mfa_enabled"])

    def test_owner_activation_rejects_existing_account_without_mfa(self):
        from unittest.mock import patch
        from crownpath.auth import create_owner, get_user_by_id

        before = get_user_by_id(self.user["user_id"])
        with patch.dict(os.environ, {
            "CROWNPATH_OWNER_EMAIL": self.email,
            "CROWNPATH_OWNER_ACTIVATION_CODE": "synthetic-activation-code",
        }):
            with self.assertRaisesRegex(ValueError, "separately verified Owner provisioning"):
                create_owner("Changed Owner", self.email, "Replacement-Password-2026!", "synthetic-activation-code")

        after = get_user_by_id(self.user["user_id"])
        self.assertEqual(after["role"], before["role"])
        self.assertEqual(after["password_hash"], before["password_hash"])
        self.assertFalse(after["mfa_enabled"])

    def test_owner_activation_endpoint_does_not_issue_session_for_mfa_account(self):
        self.enable_mfa()
        self.client.cookies.clear()
        with __import__("unittest.mock", fromlist=["patch"]).patch.dict(os.environ, {
            "CROWNPATH_OWNER_EMAIL": self.email,
            "CROWNPATH_OWNER_ACTIVATION_CODE": "synthetic-activation-code",
        }):
            response = self.client.post("/api/auth/owner-activation", json={
                "name": "Changed Owner",
                "email": self.email,
                "password": "Replacement-Password-2026!",
                "activation_code": "synthetic-activation-code",
            })
        self.assertEqual(response.status_code, 400, response.text)
        self.assertIsNone(self.client.cookies.get("crownpath_session"))

    def test_owner_permission_requires_mfa_but_enrollment_remains_accessible(self):
        from unittest.mock import patch
        from crownpath.auth import get_user_by_id
        db = session()
        try:
            owner = db.get(User, self.user["user_id"])
            owner.role = "OWNER"
            owner.track = "OWNER"
            db.commit()
        finally:
            db.close()
        try:
            with patch.dict(os.environ, {"CROWNPATH_OWNER_ONLY": "true"}):
                self.login_without_mfa()
                denied = self.client.get("/api/audio/stations")
                self.assertEqual(denied.status_code, 403, denied.text)
                pre_mfa_identity = self.client.get("/api/auth/me")
                self.assertEqual(pre_mfa_identity.status_code, 200, pre_mfa_identity.text)
                self.assertEqual(pre_mfa_identity.json()["permissions"], [])
                self.assertTrue(pre_mfa_identity.json()["mfa_verification_required"])
                enrollment_cookie = self.client.cookies.get("crownpath_session")
                setup = self.client.post("/api/auth/mfa/setup")
                self.assertEqual(setup.status_code, 200, setup.text)
                enabled = self.client.post("/api/auth/mfa/enable",
                                           json={"code": pyotp.TOTP(setup.json()["secret"]).now()})
                self.assertEqual(enabled.status_code, 200, enabled.text)
                verified_cookie = self.client.cookies.get("crownpath_session")
                self.assertNotEqual(enrollment_cookie, verified_cookie)
                self.assertEqual(self.client.get("/api/audio/stations").status_code, 200)
                verified_identity = self.client.get("/api/auth/me")
                self.assertFalse(verified_identity.json()["mfa_verification_required"])
                self.assertTrue(verified_identity.json()["permissions"])
                self.client.cookies.set("crownpath_session", enrollment_cookie)
                self.assertEqual(self.client.get("/api/audio/stations").status_code, 401)
        finally:
            db = session()
            try:
                owner = db.get(User, self.user["user_id"])
                owner.role = "HOME_CARE"
                owner.track = "HOME_CARE"
                db.commit()
            finally:
                db.close()

    def test_expired_verified_owner_session_is_rejected(self):
        from datetime import timedelta
        from unittest.mock import patch
        from crownpath.auth import decode_access_token, now_utc, session_mfa_verified
        db = session()
        try:
            owner = db.get(User, self.user["user_id"])
            owner.role = "OWNER"
            owner.track = "OWNER"
            db.commit()
        finally:
            db.close()
        with patch.dict(os.environ, {"CROWNPATH_OWNER_ONLY": "true"}):
            self.enable_mfa()
            token = self.client.cookies.get("crownpath_session")
            self.assertTrue(session_mfa_verified(token))
            self.assertEqual(self.client.get("/api/audio/stations").status_code, 200)
            db = session()
            try:
                for row in db.query(AuthToken).filter(
                    AuthToken.user_id == self.user["user_id"],
                    AuthToken.token_type == "SESSION",
                    AuthToken.used_at.is_(None),
                ):
                    row.expires_at = now_utc() - timedelta(minutes=1)
                db.commit()
            finally:
                db.close()
            self.assertIsNone(decode_access_token(token))
            self.assertFalse(session_mfa_verified(token))
            self.assertEqual(self.client.get("/api/audio/stations").status_code, 401)

    def test_verified_owner_session_rejected_after_logout(self):
        from unittest.mock import patch
        from crownpath.auth import decode_access_token, session_mfa_verified
        db = session()
        try:
            owner = db.get(User, self.user["user_id"])
            owner.role = "OWNER"
            owner.track = "OWNER"
            db.commit()
        finally:
            db.close()
        with patch.dict(os.environ, {"CROWNPATH_OWNER_ONLY": "true"}):
            self.enable_mfa()
            token = self.client.cookies.get("crownpath_session")
            self.assertTrue(session_mfa_verified(token))
            self.assertEqual(self.client.get("/api/audio/stations").status_code, 200)
            logged_out = self.client.post("/api/auth/logout")
            self.assertEqual(logged_out.status_code, 200, logged_out.text)
            self.assertIsNone(decode_access_token(token))
            self.assertFalse(session_mfa_verified(token))
            self.client.cookies.set("crownpath_session", token)
            self.assertEqual(self.client.get("/api/audio/stations").status_code, 401)

    def test_mfa_setup_requires_authentication(self):
        response = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(response.status_code, 401, response.text)

    def test_second_confirmation_cannot_replace_recovery_tokens(self):
        from crownpath.auth import enable_mfa
        self.login_without_mfa()
        setup = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(setup.status_code, 200, setup.text)
        code = pyotp.TOTP(setup.json()["secret"]).now()
        first = enable_mfa(self.user["user_id"], code)
        self.assertEqual(len(first), 8)
        db = session()
        try:
            before = {
                token.token_hash for token in db.query(AuthToken).filter(
                    AuthToken.user_id == self.user["user_id"],
                    AuthToken.token_type == "MFA_RECOVERY",
                ).all()
            }
        finally:
            db.close()
        self.assertEqual(len(before), 8)
        self.assertIsNone(enable_mfa(self.user["user_id"], code))
        db = session()
        try:
            after = {
                token.token_hash for token in db.query(AuthToken).filter(
                    AuthToken.user_id == self.user["user_id"],
                    AuthToken.token_type == "MFA_RECOVERY",
                ).all()
            }
        finally:
            db.close()
        self.assertEqual(after, before)

    def test_stale_mfa_setup_cannot_activate_replaced_secret(self):
        from crownpath.auth import enable_mfa, get_user_by_id
        self.login_without_mfa()
        first = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(first.status_code, 200, first.text)
        first_secret = first.json()["secret"]
        second = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(second.status_code, 200, second.text)
        second_secret = second.json()["secret"]
        self.assertNotEqual(first_secret, second_secret)
        self.assertIsNone(enable_mfa(self.user["user_id"], pyotp.TOTP(first_secret).now()))
        self.assertFalse(get_user_by_id(self.user["user_id"])["mfa_enabled"])
        codes = enable_mfa(self.user["user_id"], pyotp.TOTP(second_secret).now())
        self.assertEqual(len(codes), 8)
        self.assertTrue(get_user_by_id(self.user["user_id"])["mfa_enabled"])
        self.assertIsNone(enable_mfa(self.user["user_id"], pyotp.TOTP(first_secret).now()))

    def test_mfa_session_creation_failure_preserves_enrollment(self):
        from unittest.mock import patch
        from crownpath.auth import get_user_by_id
        self.login_without_mfa()
        setup = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(setup.status_code, 200, setup.text)
        enrollment_cookie = self.client.cookies.get("crownpath_session")
        code = pyotp.TOTP(setup.json()["secret"]).now()
        with patch("crownpath.main.create_access_token", side_effect=RuntimeError("simulated session failure")):
            with self.assertRaisesRegex(RuntimeError, "simulated session failure"):
                self.client.post("/api/auth/mfa/enable", json={"code": code})
        self.assertTrue(get_user_by_id(self.user["user_id"])["mfa_enabled"])
        self.assertEqual(self.client.cookies.get("crownpath_session"), enrollment_cookie)
        self.assertEqual(self.client.get("/api/auth/me").status_code, 401)
        self.client.cookies.clear()
        login = self.client.post("/api/auth/login", json={"email": self.email, "password": self.password})
        self.assertEqual(login.status_code, 200, login.text)
        self.assertTrue(login.json()["mfa_required"])
        verified = self.client.post("/api/auth/mfa/verify", json={
            "challenge": login.json()["challenge"], "code": pyotp.TOTP(setup.json()["secret"]).now(),
        })
        self.assertEqual(verified.status_code, 200, verified.text)
        self.assertTrue(verified.json()["authenticated"])

    def test_recovery_token_write_failure_rolls_back_mfa_activation(self):
        from unittest.mock import patch
        from sqlalchemy.orm import Session as SqlAlchemySession
        from crownpath.auth import enable_mfa, get_user_by_id
        setup_login = self.login_without_mfa()
        self.assertEqual(setup_login.status_code, 200)
        setup = self.client.post("/api/auth/mfa/setup")
        self.assertEqual(setup.status_code, 200, setup.text)
        secret = setup.json()["secret"]
        original_commit = SqlAlchemySession.commit

        def fail_recovery_commit(db):
            if any(isinstance(item, AuthToken) and item.token_type == "MFA_RECOVERY"
                   for item in db.new):
                raise RuntimeError("simulated recovery-token persistence failure")
            return original_commit(db)

        with patch.object(SqlAlchemySession, "commit", fail_recovery_commit):
            with self.assertRaisesRegex(RuntimeError, "simulated recovery-token"):
                enable_mfa(self.user["user_id"], pyotp.TOTP(secret).now())
        self.assertFalse(get_user_by_id(self.user["user_id"])["mfa_enabled"])
        db = session()
        try:
            recovery_count = db.query(AuthToken).filter(
                AuthToken.user_id == self.user["user_id"],
                AuthToken.token_type == "MFA_RECOVERY",
            ).count()
            self.assertEqual(recovery_count, 0)
        finally:
            db.close()

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

    def test_recovery_code_hash_is_keyed_and_user_bound(self):
        code = "12345678"
        plain_sha256 = hashlib.sha256(code.encode("utf-8")).hexdigest()
        first = _hash_mfa_recovery_code(self.user["user_id"], code)
        second = _hash_mfa_recovery_code("CP-USR-DIFFERENT", code)
        self.assertNotEqual(first, plain_sha256)
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_atomic_recovery_code_consumption_allows_only_one_success(self):
        _, recovery_codes = self.enable_mfa()
        recovery_code = recovery_codes[0]
        first = consume_mfa_recovery_code(self.user["user_id"], recovery_code)
        second = consume_mfa_recovery_code(self.user["user_id"], recovery_code)
        self.assertTrue(first)
        self.assertFalse(second)

        db = session()
        try:
            token = db.query(AuthToken).filter(
                AuthToken.user_id == self.user["user_id"],
                AuthToken.token_hash == _hash_mfa_recovery_code(self.user["user_id"], recovery_code),
                AuthToken.token_type == "MFA_RECOVERY",
            ).one()
            self.assertIsNotNone(token.used_at)
        finally:
            db.close()

    def test_recovery_code_is_one_time_use_through_login(self):
        _, recovery_codes = self.enable_mfa()
        recovery_code = recovery_codes[0]
        db = session()
        try:
            rows = db.query(AuthToken).filter(AuthToken.user_id == self.user["user_id"], AuthToken.token_type == "MFA_RECOVERY").all()
            self.assertEqual(len(rows), 8)
            stored_hashes = {row.token_hash for row in rows}
            self.assertFalse(any(code in stored_hashes for code in recovery_codes))
            plain_hashes = {hashlib.sha256(code.encode("utf-8")).hexdigest() for code in recovery_codes}
            self.assertTrue(stored_hashes.isdisjoint(plain_hashes))
            expected_hashes = {_hash_mfa_recovery_code(self.user["user_id"], code) for code in recovery_codes}
            self.assertEqual(stored_hashes, expected_hashes)
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

        for _ in range(5):
            failed = self.client.post("/api/auth/mfa/verify", json={"challenge": challenge, "code": "000000"})
            self.assertEqual(failed.status_code, 401, failed.text)

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
