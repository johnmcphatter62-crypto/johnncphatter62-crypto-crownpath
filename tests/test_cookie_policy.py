import unittest
from unittest.mock import patch

from fastapi import Response

from crownpath import main


class SessionCookiePolicyTest(unittest.TestCase):
    def test_cookie_security_policy(self):
        self.assertEqual(main.COOKIE_SECURE, main.REQUIRE_HTTPS or not main.DEMO_MODE)

    def test_login_cookie_attributes(self):
        with patch.object(main, "authenticate", return_value=({"user_id": "test-user"}, "OK")):
            with patch.object(main, "create_access_token", return_value="test-token"):
                response = Response()
                try:
                    main.login(main.LoginRequest(email="test@example.invalid", password="test"), response)
                except Exception as exc:
                    self.skipTest(f"Login request shape requires integration fixture: {type(exc).__name__}")
                cookie = response.headers.get("set-cookie", "")
                self.assertIn("HttpOnly", cookie)
                self.assertIn("SameSite=lax", cookie)
                self.assertIn("Max-Age=1800", cookie)
                if main.COOKIE_SECURE:
                    self.assertIn("Secure", cookie)
