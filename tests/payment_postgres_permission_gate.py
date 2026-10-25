"""Permission gate for disposable payment PostgreSQL integration tests.

Import this module before creating a DB engine or importing application modules.
"""
import os
import unittest
from urllib.parse import urlsplit


def require_disposable_postgres_permission():
    url = os.environ.get("CROWNPATH_TEST_POSTGRES_URL", "")
    if not url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise unittest.SkipTest("Explicit PostgreSQL test URL required")
    parsed = urlsplit(url)
    if (parsed.hostname or "").lower() not in ("localhost", "127.0.0.1", "::1"):
        raise unittest.SkipTest("Only localhost disposable PostgreSQL is permitted")
    name = parsed.path.lstrip("/").lower()
    if not name or "disposable" not in name:
        raise unittest.SkipTest("Database name must explicitly include disposable")
    if os.environ.get("CROWNPATH_DATABASE_URL") != url:
        raise unittest.SkipTest("Configured database must match disposable test URL")
    if os.environ.get("CROWNPATH_ENV", "").lower() != "staging":
        raise unittest.SkipTest("Staging-only test")
    if os.environ.get("CROWNPATH_TEST_DB_DISPOSABLE") != "YES":
        raise unittest.SkipTest("Disposable database confirmation required")
    if os.environ.get("CROWNPATH_OWNER_LAUNCH_APPROVED", "").lower() == "true":
        raise unittest.SkipTest("Owner launch must remain disabled")
    return url
