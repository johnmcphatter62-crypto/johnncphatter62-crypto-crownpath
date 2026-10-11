import os
import unittest
import uuid
from datetime import datetime, timedelta, timezone

import jwt

os.environ.setdefault("CROWNPATH_ENV", "staging")
os.environ.setdefault("CROWNPATH_SECRET_KEY", "ci-only-secret-key-for-auth-tests-123456789")

from sqlalchemy import delete

from crownpath.auth import (
    ALGORITHM,
    SECRET_KEY,
    authenticate,
    create_access_token,
    create_user,
    decode_access_token,
    get_user_by_email,
    revoke_access_token,
    update_password,
)
from crownpath.database import init_db, session
from crownpath.models import AuthToken, User


class PostgresAuthIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_registration_login_token_and_cleanup(self):
        suffix = uuid.uuid4().hex[:10]
        email = f"crownpath-ci-{suffix}@example.invalid"
        password = "CrownPath-CI-Auth-2026!"

        created = create_user("CrownPath CI", email, password, "HOME_CARE")
        self.assertEqual(created["email"], email)
        self.assertEqual(created["role"], "HOME_CARE")

        persisted = get_user_by_email(email)
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted["user_id"], created["user_id"])

        authenticated, status = authenticate(email, password)
        self.assertEqual(status, "OK")
        self.assertEqual(authenticated["user_id"], created["user_id"])

        token = create_access_token(created["user_id"])
        self.assertEqual(decode_access_token(token), created["user_id"])

        db = session()
        try:
            db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
            db.execute(delete(User).where(User.user_id == created["user_id"]))
            db.commit()
        finally:
            db.close()

        self.assertIsNone(get_user_by_email(email))

    def test_session_without_required_claims_is_rejected(self):
        now = datetime.now(timezone.utc)
        for claims in (
            {"sub": "CP-USR-MISSING-JTI", "purpose": "session"},
            {"sub": "CP-USR-MISSING-PURPOSE", "jti": uuid.uuid4().hex},
            {"sub": "CP-USR-EMPTY-JTI", "purpose": "session", "jti": ""},
        ):
            token = jwt.encode(
                {**claims, "iat": now, "exp": now + timedelta(minutes=5)},
                SECRET_KEY,
                algorithm=ALGORITHM,
            )
            self.assertIsNone(decode_access_token(token))

    def test_logout_revokes_session_and_rejects_replay(self):
        from fastapi.testclient import TestClient
        from crownpath.main import app

        email = f"crownpath-logout-{uuid.uuid4().hex[:10]}@example.invalid"
        created = create_user("Logout Test", email, "CrownPath-Logout-Test-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            self.assertEqual(decode_access_token(token), created["user_id"])
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            response = client.post("/api/auth/logout")
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(decode_access_token(token))
            self.assertFalse(revoke_access_token(token))
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_token_without_session_purpose_cannot_revoke_valid_session(self):
        email = f"crownpath-revoke-{uuid.uuid4().hex[:10]}@example.invalid"
        created = create_user("Revoke Purpose Test", email, "CrownPath-Revoke-Test-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            payload.pop("purpose")
            malformed = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
            self.assertFalse(revoke_access_token(malformed))
            self.assertEqual(decode_access_token(token), created["user_id"])
            self.assertTrue(revoke_access_token(token))
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_logout_database_failure_is_not_reported_as_success(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app)
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", side_effect=RuntimeError("database unavailable")):
            response = client.post("/api/auth/logout")
        self.assertEqual(response.status_code, 503)
        self.assertNotEqual(response.json(), {"authenticated": False})

    def test_database_expired_session_is_rejected(self):
        email = f"crownpath-db-expired-{uuid.uuid4().hex[:10]}@example.invalid"
        created = create_user("Expired Session Test", email, "CrownPath-Expired-Test-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            self.assertEqual(decode_access_token(token), created["user_id"])
            db = session()
            try:
                from sqlalchemy import update
                db.execute(
                    update(AuthToken)
                    .where(AuthToken.user_id == created["user_id"], AuthToken.token_type == "SESSION")
                    .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=5))
                )
                db.commit()
            finally:
                db.close()
            self.assertIsNone(decode_access_token(token))
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_deactivated_account_cannot_access_authenticated_endpoint(self):
        from fastapi.testclient import TestClient
        from crownpath.main import app

        email = f"crownpath-inactive-{uuid.uuid4().hex[:10]}@example.invalid"
        created = create_user("Inactive Account Test", email, "CrownPath-Inactive-Test-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            db = session()
            try:
                from sqlalchemy import update
                db.execute(update(User).where(User.user_id == created["user_id"]).values(active=False))
                db.commit()
            finally:
                db.close()
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_expired_session_token_is_rejected(self):
        now = datetime.now(timezone.utc)
        expired = jwt.encode(
            {
                "sub": "CP-USR-EXPIRED",
                "purpose": "session",
                "iat": now - timedelta(minutes=31),
                "exp": now - timedelta(seconds=1),
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        self.assertIsNone(decode_access_token(expired))

    def test_mfa_challenge_token_cannot_be_used_as_session(self):
        now = datetime.now(timezone.utc)
        challenge = jwt.encode(
            {
                "sub": "CP-USR-CHALLENGE",
                "purpose": "mfa_challenge",
                "iat": now,
                "exp": now + timedelta(minutes=5),
                "jti": uuid.uuid4().hex,
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        self.assertIsNone(decode_access_token(challenge))

    def test_revoked_session_token_cannot_be_reused(self):
        suffix = uuid.uuid4().hex[:10]
        email = f"crownpath-session-{suffix}@example.invalid"
        password = "CrownPath-Session-Test-2026!"
        created = create_user("CrownPath Session", email, password, "HOME_CARE")
        token = create_access_token(created["user_id"])

        self.assertEqual(decode_access_token(token), created["user_id"])
        self.assertTrue(revoke_access_token(token))
        self.assertIsNone(decode_access_token(token))
        self.assertFalse(revoke_access_token(token))

        db = session()
        try:
            db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
            db.execute(delete(User).where(User.user_id == created["user_id"]))
            db.commit()
        finally:
            db.close()

    def test_password_change_revokes_all_active_sessions(self):
        suffix = uuid.uuid4().hex[:10]
        email = f"crownpath-password-reset-{suffix}@example.invalid"
        old_password = "CrownPath-Old-Password-2026!"
        new_password = "CrownPath-New-Password-2026!"
        created = create_user("CrownPath Password Reset", email, old_password, "HOME_CARE")
        first_token = create_access_token(created["user_id"])
        second_token = create_access_token(created["user_id"])

        self.assertEqual(decode_access_token(first_token), created["user_id"])
        self.assertEqual(decode_access_token(second_token), created["user_id"])

        update_password(created["user_id"], new_password)

        self.assertIsNone(decode_access_token(first_token))
        self.assertIsNone(decode_access_token(second_token))
        old_login, old_status = authenticate(email, old_password)
        self.assertIsNone(old_login)
        self.assertEqual(old_status, "INVALID")
        new_login, new_status = authenticate(email, new_password)
        self.assertEqual(new_status, "OK")
        self.assertEqual(new_login["user_id"], created["user_id"])

        db = session()
        try:
            db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
            db.execute(delete(User).where(User.user_id == created["user_id"]))
            db.commit()
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
