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
            response = client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
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

    def test_cross_origin_cookie_authenticated_logout_is_blocked(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app, base_url="http://testserver")
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", return_value=True) as revoke:
            denied = client.post("/api/auth/logout", headers={"Origin": "https://attacker.example"})
            self.assertEqual(denied.status_code, 403)
            revoke.assert_not_called()
            allowed = client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
            self.assertEqual(allowed.status_code, 200)
            revoke.assert_called_once()

    def test_authenticated_mutation_requires_verifiable_origin(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app, base_url="http://testserver")
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", return_value=True) as revoke:
            self.assertEqual(client.post("/api/auth/logout").status_code, 403)
            self.assertEqual(client.post("/api/auth/logout", headers={"Referer": "https://other.example/"}).status_code, 403)
            self.assertEqual(client.post("/api/auth/logout", headers={"Referer": "http://testserver/classroom"}).status_code, 200)
            revoke.assert_called_once()

    def test_forged_forwarded_headers_do_not_bypass_origin_checks(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app, base_url="http://testserver")
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", return_value=True) as revoke:
            for headers in (
                {"Origin": "https://attacker.example", "X-Forwarded-Host": "attacker.example"},
                {"Origin": "https://attacker.example", "X-Forwarded-Proto": "https"},
                {"Origin": "http://testserver:444", "X-Forwarded-Port": "444"},
                {"Origin": "https://testserver", "X-Forwarded-Proto": "https"},
                {"Origin": "null"},
                {"Origin": "http://testserver.evil.example"},
                {"Origin": "http://testserver@attacker.example"},
            ):
                with self.subTest(headers=headers):
                    self.assertEqual(client.post("/api/auth/logout", headers=headers).status_code, 403)
            revoke.assert_not_called()

    def test_origin_takes_precedence_over_referer(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app, base_url="http://testserver")
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", return_value=True) as revoke:
            rejected = client.post(
                "/api/auth/logout",
                headers={"Origin": "https://attacker.example", "Referer": "http://testserver/classroom"},
            )
            self.assertEqual(rejected.status_code, 403)
            accepted = client.post(
                "/api/auth/logout",
                headers={"Origin": "http://testserver", "Referer": "https://attacker.example/"},
            )
            self.assertEqual(accepted.status_code, 200)
            revoke.assert_called_once()

    def test_malformed_origin_is_not_rescued_by_referer(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app, base_url="http://testserver")
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", return_value=True) as revoke:
            for origin in ("", "null", "http://testserver/path", "http://testserver?query=1"):
                with self.subTest(origin=origin):
                    response = client.post(
                        "/api/auth/logout",
                        headers={"Origin": origin, "Referer": "http://testserver/classroom"},
                    )
                    self.assertEqual(response.status_code, 403)
            revoke.assert_not_called()

    def test_security_headers_are_present_on_successful_requests(self):
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app)
        response = client.get("/api/health")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertEqual(response.headers.get("referrer-policy"), "no-referrer")
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_denied_cross_origin_request_is_not_cacheable(self):
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app)
        client.cookies.set("crownpath_session", "simulated-session-token")
        response = client.post("/api/auth/logout", headers={"Origin": "https://attacker.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_hsts_follows_explicit_https_requirement(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app)
        with patch.dict(os.environ, {"CROWNPATH_REQUIRE_HTTPS": "false"}):
            response = client.get("/api/health")
            self.assertNotIn("strict-transport-security", response.headers)
        with patch.dict(os.environ, {"CROWNPATH_REQUIRE_HTTPS": "true"}):
            response = client.get("/api/health")
            self.assertEqual(
                response.headers.get("strict-transport-security"),
                "max-age=31536000; includeSubDomains",
            )

    def test_logout_revocation_is_called_only_once(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app)
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", return_value=True) as revoke:
            response = client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
        self.assertEqual(response.status_code, 200)
        revoke.assert_called_once_with("simulated-session-token")

    def test_logout_database_failure_is_not_reported_as_success(self):
        from unittest.mock import patch
        from fastapi.testclient import TestClient
        from crownpath.main import app

        client = TestClient(app)
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch("crownpath.main.revoke_access_token", side_effect=RuntimeError("database unavailable")):
            response = client.post("/api/auth/logout", headers={"Origin": "http://testserver"})
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

    def test_database_expired_session_cannot_access_authenticated_endpoint(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import update
        from crownpath.main import app

        email = f"crownpath-expired-http-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Expired HTTP Session", email, "CrownPath-Expired-HTTP-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            db = session()
            try:
                db.execute(
                    update(AuthToken)
                    .where(AuthToken.user_id == created["user_id"], AuthToken.token_type == "SESSION")
                    .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=5))
                )
                db.commit()
            finally:
                db.close()
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            response = client.get("/api/auth/me")
            self.assertEqual(response.status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_revoked_session_cannot_access_authenticated_endpoint(self):
        from fastapi.testclient import TestClient
        from crownpath.main import app

        email = f"crownpath-revoked-http-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Revoked HTTP Session", email, "CrownPath-Revoked-HTTP-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            self.assertTrue(revoke_access_token(token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_password_change_invalidates_existing_browser_sessions(self):
        from fastapi.testclient import TestClient
        from crownpath.main import app

        email = f"crownpath-password-http-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Password HTTP Session", email, "CrownPath-Old-HTTP-2026!", "HOME_CARE")
        first_token = create_access_token(created["user_id"])
        second_token = create_access_token(created["user_id"])
        try:
            first_client = TestClient(app)
            second_client = TestClient(app)
            first_client.cookies.set("crownpath_session", first_token)
            second_client.cookies.set("crownpath_session", second_token)
            self.assertEqual(first_client.get("/api/auth/me").status_code, 200)
            self.assertEqual(second_client.get("/api/auth/me").status_code, 200)
            update_password(created["user_id"], "CrownPath-New-HTTP-2026!")
            self.assertEqual(first_client.get("/api/auth/me").status_code, 401)
            self.assertEqual(second_client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_deactivation_invalidates_multiple_existing_browser_sessions(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import update
        from crownpath.main import app

        email = f"crownpath-disabled-http-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Disabled HTTP Sessions", email, "CrownPath-Disabled-HTTP-2026!", "HOME_CARE")
        first_token = create_access_token(created["user_id"])
        second_token = create_access_token(created["user_id"])
        try:
            first_client = TestClient(app)
            second_client = TestClient(app)
            first_client.cookies.set("crownpath_session", first_token)
            second_client.cookies.set("crownpath_session", second_token)
            self.assertEqual(first_client.get("/api/auth/me").status_code, 200)
            self.assertEqual(second_client.get("/api/auth/me").status_code, 200)
            db = session()
            try:
                db.execute(update(User).where(User.user_id == created["user_id"]).values(active=False))
                db.commit()
            finally:
                db.close()
            self.assertEqual(first_client.get("/api/auth/me").status_code, 401)
            self.assertEqual(second_client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_reactivation_does_not_restore_old_browser_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_active
        from crownpath.main import app

        email = f"crownpath-reactivate-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Reactivation Session Test", email, "CrownPath-Reactivate-2026!", "HOME_CARE")
        old_token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", old_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_active(created["user_id"], False)
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            set_user_active(created["user_id"], True)
            self.assertIsNone(decode_access_token(old_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            new_token = create_access_token(created["user_id"])
            client.cookies.set("crownpath_session", new_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_role_change_deactivation_and_reactivation_keep_old_session_revoked(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role, set_user_active
        from crownpath.main import app

        email = f"crownpath-role-disabled-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Role Deactivation Test", email, "CrownPath-Role-Disabled-2026!", "HOME_CARE")
        old_token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", old_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "INSTRUCTOR", False)
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            set_user_active(created["user_id"], True)
            self.assertIsNone(decode_access_token(old_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_unchanged_role_update_preserves_valid_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-same-role-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Same Role Test", email, "CrownPath-Same-Role-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "HOME_CARE", True)
            self.assertEqual(decode_access_token(token), created["user_id"])
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_role_change_revokes_multiple_browser_sessions(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-role-multi-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Role Multi Session Test", email, "CrownPath-Role-Multi-2026!", "HOME_CARE")
        first_token = create_access_token(created["user_id"])
        second_token = create_access_token(created["user_id"])
        try:
            first_client = TestClient(app)
            second_client = TestClient(app)
            first_client.cookies.set("crownpath_session", first_token)
            second_client.cookies.set("crownpath_session", second_token)
            self.assertEqual(first_client.get("/api/auth/me").status_code, 200)
            self.assertEqual(second_client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "INSTRUCTOR", True)
            self.assertIsNone(decode_access_token(first_token))
            self.assertIsNone(decode_access_token(second_token))
            self.assertEqual(first_client.get("/api/auth/me").status_code, 401)
            self.assertEqual(second_client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_deactivation_api_revokes_multiple_browser_sessions(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_active
        from crownpath.main import app

        email = f"crownpath-disable-multi-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Disable Multi Session Test", email, "CrownPath-Disable-Multi-2026!", "HOME_CARE")
        first_token = create_access_token(created["user_id"])
        second_token = create_access_token(created["user_id"])
        try:
            clients = [TestClient(app), TestClient(app)]
            for client, token in zip(clients, [first_token, second_token]):
                client.cookies.set("crownpath_session", token)
                self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_active(created["user_id"], False)
            for client, token in zip(clients, [first_token, second_token]):
                self.assertIsNone(decode_access_token(token))
                self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_owner_cannot_be_disabled_or_reassigned_by_standard_account_functions(self):
        from sqlalchemy import update
        from crownpath.auth import set_user_active, set_user_role

        email = f"crownpath-owner-guard-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Synthetic Owner Guard", email, "CrownPath-Owner-Guard-2026!", "HOME_CARE")
        try:
            # Synthetic owner exists only in disposable CI PostgreSQL.
            db = session()
            try:
                db.execute(update(User).where(User.user_id == created["user_id"]).values(role="OWNER", track="OWNER"))
                db.commit()
            finally:
                db.close()
            with self.assertRaisesRegex(ValueError, "Owner account cannot be disabled"):
                set_user_active(created["user_id"], False)
            with self.assertRaisesRegex(ValueError, "Owner role cannot be changed"):
                set_user_role(created["user_id"], "INSTRUCTOR", False)
            db = session()
            try:
                owner = db.get(User, created["user_id"])
                self.assertEqual(owner.role, "OWNER")
                self.assertTrue(owner.active)
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_rejected_owner_account_changes_preserve_existing_session(self):
        from fastapi.testclient import TestClient
        from sqlalchemy import update
        from crownpath.auth import set_user_active, set_user_role
        from crownpath.main import app

        email = f"crownpath-owner-session-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Synthetic Owner Session", email, "CrownPath-Owner-Session-2026!", "HOME_CARE")
        try:
            db = session()
            try:
                db.execute(update(User).where(User.user_id == created["user_id"]).values(role="OWNER", track="OWNER"))
                db.commit()
            finally:
                db.close()
            token = create_access_token(created["user_id"])
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(decode_access_token(token), created["user_id"])
            with self.assertRaises(ValueError):
                set_user_active(created["user_id"], False)
            with self.assertRaises(ValueError):
                set_user_role(created["user_id"], "INSTRUCTOR", False)
            self.assertEqual(decode_access_token(token), created["user_id"])
            db = session()
            try:
                owner = db.get(User, created["user_id"])
                self.assertTrue(owner.active)
                self.assertEqual(owner.role, "OWNER")
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_self_registration_and_role_update_cannot_grant_owner_role(self):
        from crownpath.auth import set_user_role

        email = f"crownpath-owner-denied-{uuid.uuid4().hex[:10]}@example.com"
        with self.assertRaisesRegex(ValueError, "cannot be self-assigned"):
            create_user("Owner Self Registration", email, "CrownPath-Owner-Denied-2026!", "OWNER")

        created = create_user("Role Elevation Guard", email, "CrownPath-Role-Denied-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            with self.assertRaisesRegex(ValueError, "Unsupported staff or learner role"):
                set_user_role(created["user_id"], "OWNER", True)
            self.assertEqual(decode_access_token(token), created["user_id"])
            db = session()
            try:
                user = db.get(User, created["user_id"])
                self.assertEqual(user.role, "HOME_CARE")
                self.assertTrue(user.active)
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_unsupported_role_update_preserves_account_and_session(self):
        from crownpath.auth import set_user_role

        email = f"crownpath-invalid-role-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Invalid Role Test", email, "CrownPath-Invalid-Role-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            with self.assertRaisesRegex(ValueError, "Unsupported staff or learner role"):
                set_user_role(created["user_id"], "SYSTEM_ADMIN", False)
            self.assertEqual(decode_access_token(token), created["user_id"])
            db = session()
            try:
                user = db.get(User, created["user_id"])
                self.assertEqual(user.role, "HOME_CARE")
                self.assertEqual(user.track, "HOME_CARE")
                self.assertTrue(user.active)
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_unknown_user_role_update_does_not_affect_existing_account(self):
        from crownpath.auth import set_user_role, set_user_active

        email = f"crownpath-missing-user-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Unaffected User Test", email, "CrownPath-Missing-User-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        missing_id = f"CP-USR-MISSING-{uuid.uuid4().hex[:12].upper()}"
        try:
            with self.assertRaisesRegex(ValueError, "User not found"):
                set_user_role(missing_id, "INSTRUCTOR", False)
            with self.assertRaisesRegex(ValueError, "User not found"):
                set_user_active(missing_id, False)
            self.assertEqual(decode_access_token(token), created["user_id"])
            db = session()
            try:
                user = db.get(User, created["user_id"])
                self.assertEqual(user.role, "HOME_CARE")
                self.assertTrue(user.active)
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_redundant_activation_preserves_valid_sessions(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_active
        from crownpath.main import app

        email = f"crownpath-still-active-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Already Active Test", email, "CrownPath-Still-Active-2026!", "HOME_CARE")
        tokens = [create_access_token(created["user_id"]) for _ in range(2)]
        try:
            clients = [TestClient(app), TestClient(app)]
            for client, token in zip(clients, tokens):
                client.cookies.set("crownpath_session", token)
                self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_active(created["user_id"], True)
            for client, token in zip(clients, tokens):
                self.assertEqual(decode_access_token(token), created["user_id"])
                self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_repeated_deactivation_never_restores_revoked_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_active
        from crownpath.main import app

        email = f"crownpath-disable-twice-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Repeated Deactivation Test", email, "CrownPath-Disable-Twice-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_active(created["user_id"], False)
            self.assertIsNone(decode_access_token(token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            set_user_active(created["user_id"], False)
            self.assertIsNone(decode_access_token(token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            set_user_active(created["user_id"], True)
            self.assertIsNone(decode_access_token(token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_role_change_then_reversal_never_restores_original_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-role-reverse-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Role Reversal Test", email, "CrownPath-Role-Reverse-2026!", "HOME_CARE")
        original_token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", original_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "INSTRUCTOR", True)
            self.assertIsNone(decode_access_token(original_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            set_user_role(created["user_id"], "HOME_CARE", True)
            self.assertIsNone(decode_access_token(original_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            new_token = create_access_token(created["user_id"])
            client.cookies.set("crownpath_session", new_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_each_role_change_revokes_sessions_issued_under_previous_role(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-role-sequence-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Sequential Role Test", email, "CrownPath-Role-Sequence-2026!", "HOME_CARE")
        first_token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", first_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "INSTRUCTOR", True)
            self.assertIsNone(decode_access_token(first_token))
            second_token = create_access_token(created["user_id"])
            client.cookies.set("crownpath_session", second_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "HOME_CARE", True)
            self.assertIsNone(decode_access_token(first_token))
            self.assertIsNone(decode_access_token(second_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            third_token = create_access_token(created["user_id"])
            client.cookies.set("crownpath_session", third_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_unchanged_role_with_deactivation_revokes_existing_sessions(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role, set_user_active
        from crownpath.main import app

        email = f"crownpath-same-role-disable-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Same Role Disable Test", email, "CrownPath-Same-Role-Disable-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_role(created["user_id"], "HOME_CARE", False)
            self.assertIsNone(decode_access_token(token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            set_user_active(created["user_id"], True)
            self.assertIsNone(decode_access_token(token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_role_management_reactivation_does_not_restore_revoked_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role, set_user_active
        from crownpath.main import app

        email = f"crownpath-role-reactivate-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Role Reactivation Test", email, "CrownPath-Role-Reactivate-2026!", "HOME_CARE")
        old_token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", old_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            set_user_active(created["user_id"], False)
            self.assertIsNone(decode_access_token(old_token))
            set_user_role(created["user_id"], "HOME_CARE", True)
            self.assertIsNone(decode_access_token(old_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
            new_token = create_access_token(created["user_id"])
            client.cookies.set("crownpath_session", new_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_lowercase_role_change_still_revokes_existing_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-lowercase-role-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Lowercase Role Test", email, "CrownPath-Lowercase-Role-2026!", "HOME_CARE")
        old_token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", old_token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            updated = set_user_role(created["user_id"], "instructor", True)
            self.assertEqual(updated["role"], "INSTRUCTOR")
            self.assertIsNone(decode_access_token(old_token))
            self.assertEqual(client.get("/api/auth/me").status_code, 401)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_lowercase_unchanged_role_preserves_existing_session(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-lowercase-same-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Lowercase Same Role Test", email, "CrownPath-Lowercase-Same-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            updated = set_user_role(created["user_id"], "home_care", True)
            self.assertEqual(updated["role"], "HOME_CARE")
            self.assertEqual(decode_access_token(token), created["user_id"])
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == created["user_id"]))
                db.execute(delete(User).where(User.user_id == created["user_id"]))
                db.commit()
            finally:
                db.close()

    def test_invalid_role_with_deactivation_request_is_atomic(self):
        from fastapi.testclient import TestClient
        from crownpath.auth import set_user_role
        from crownpath.main import app

        email = f"crownpath-invalid-atomic-{uuid.uuid4().hex[:10]}@example.com"
        created = create_user("Invalid Atomic Role Test", email, "CrownPath-Invalid-Atomic-2026!", "HOME_CARE")
        token = create_access_token(created["user_id"])
        try:
            client = TestClient(app)
            client.cookies.set("crownpath_session", token)
            self.assertEqual(client.get("/api/auth/me").status_code, 200)
            with self.assertRaises(ValueError):
                set_user_role(created["user_id"], "not_a_role", False)
            self.assertEqual(decode_access_token(token), created["user_id"])
            response = client.get("/api/auth/me")
            self.assertEqual(response.status_code, 200)
            db = session()
            try:
                user = db.get(User, created["user_id"])
                self.assertEqual(user.role, "HOME_CARE")
                self.assertTrue(user.active)
            finally:
                db.close()
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
