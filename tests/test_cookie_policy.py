import unittest
from unittest.mock import patch

from fastapi import Response

from crownpath import main


class SessionCookiePolicyTest(unittest.TestCase):
    def test_cookie_security_policy(self):
        self.assertEqual(main.COOKIE_SECURE, main.REQUIRE_HTTPS or not main.DEMO_MODE)

    def test_login_cookie_attributes(self):
        user = {
            "user_id": "ci-cookie-user",
            "role": "OWNER",
            "mfa_enabled": False,
            "active": True,
            "email": "test@example.com",
        }
        with patch.object(main, "authenticate", return_value=(user, "OK")):
            with patch.object(main, "role_access_approved", return_value=True):
                with patch.object(main, "create_access_token", return_value="ci-cookie-token"):
                    with patch.object(main, "public_user", return_value={"user_id": "ci-cookie-user"}):
                        response = Response()
                        result = main.login(
                            main.LoginRequest(email="test@example.com", password="ci-test-only"),
                            response,
                        )
        self.assertTrue(result["authenticated"])
        cookie = response.headers.get("set-cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertIn("Max-Age=1800", cookie)
        self.assertIn("Path=/", cookie)
        if main.COOKIE_SECURE:
            self.assertIn("Secure", cookie)
        else:
            self.assertNotIn("Secure", cookie)

    def test_logout_clears_session_cookie_after_revocation(self):
        from fastapi.testclient import TestClient

        client = TestClient(main.app)
        client.cookies.set("crownpath_session", "simulated-session-token")
        with patch.object(main, "revoke_access_token", return_value=True) as revoke:
            response = client.post(
                "/api/auth/logout",
                headers={"Origin": "http://testserver"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"authenticated": False})
        cookie = response.headers.get("set-cookie", "")
        self.assertIn("crownpath_session=", cookie)
        self.assertIn("Max-Age=0", cookie)
        self.assertIn("Path=/", cookie)
        revoke.assert_called_once_with("simulated-session-token")
