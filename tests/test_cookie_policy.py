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
            "email": "test@example.invalid",
        }
        with patch.object(main, "authenticate", return_value=(user, "OK")):
            with patch.object(main, "role_access_approved", return_value=True):
                with patch.object(main, "create_access_token", return_value="ci-cookie-token"):
                    with patch.object(main, "public_user", return_value={"user_id": "ci-cookie-user"}):
                        response = Response()
                        result = main.login(
                            main.LoginRequest(email="test@example.invalid", password="ci-test-only"),
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
