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


if __name__ == "__main__":
    unittest.main()
