"""Opt-in MFA race test against a disposable PostgreSQL database.

Run ONLY with CROWNPATH_TEST_POSTGRES_URL pointing to an isolated test database:
  CROWNPATH_ENV=staging CROWNPATH_DATABASE_URL="$CROWNPATH_TEST_POSTGRES_URL" \
    python -m unittest tests.test_mfa_postgres_concurrency -v

This test creates and deletes its own synthetic user. Never point it at production.
"""
import os
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

# Guard before importing CrownPath modules (which initialize the DB engine).
test_url = os.environ.get("CROWNPATH_TEST_POSTGRES_URL", "")
configured_url = os.environ.get("CROWNPATH_DATABASE_URL", "")
if not test_url or not test_url.startswith(("postgresql://", "postgresql+psycopg://")):
    raise unittest.SkipTest("An explicit isolated PostgreSQL test URL is required")
if configured_url != test_url:
    raise unittest.SkipTest("CROWNPATH_DATABASE_URL must exactly match test URL")
if os.environ.get("CROWNPATH_ENV", "").lower() != "staging":
    raise unittest.SkipTest("Only staging environment is permitted")
if os.environ.get("CROWNPATH_TEST_DB_DISPOSABLE") != "YES":
    raise unittest.SkipTest("Set CROWNPATH_TEST_DB_DISPOSABLE=YES after confirming isolation")

import pyotp
from sqlalchemy import delete, select

from crownpath.auth import create_user, enable_mfa, start_mfa_setup, get_user_by_id
from crownpath.database import init_db, session
from crownpath.models import AuthToken, User


class PostgresMfaConcurrencyTest(unittest.TestCase):
    def test_two_confirmations_single_winner(self):
        init_db()
        email = f"synthetic-mfa-{uuid.uuid4().hex}@example.invalid"
        user = create_user("Synthetic MFA Race", email, "Disposable-Test-Only-2026!", "HOME_CARE")
        user_id = user["user_id"]
        try:
            secret = start_mfa_setup(user_id)
            code = pyotp.TOTP(secret).now()
            gate = Barrier(2)

            def confirm():
                gate.wait(timeout=15)
                return enable_mfa(user_id, code)

            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(confirm)
                second = pool.submit(confirm)
                outcomes = [first.result(timeout=30), second.result(timeout=30)]

            successful = [result for result in outcomes if result is not None]
            self.assertEqual(len(successful), 1)
            self.assertEqual(len(successful[0]), 8)
            self.assertTrue(get_user_by_id(user_id)["mfa_enabled"])
            db = session()
            try:
                hashes = db.scalars(select(AuthToken.token_hash).where(
                    AuthToken.user_id == user_id,
                    AuthToken.token_type == "MFA_RECOVERY",
                )).all()
                self.assertEqual(len(hashes), 8)
                self.assertEqual(len(set(hashes)), 8)
            finally:
                db.close()
        finally:
            db = session()
            try:
                db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
                db.execute(delete(User).where(User.user_id == user_id))
                db.commit()
            finally:
                db.close()
