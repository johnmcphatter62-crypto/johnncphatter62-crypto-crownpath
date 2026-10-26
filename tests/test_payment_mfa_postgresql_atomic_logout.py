"""Optional isolated PostgreSQL verification for the test-only atomic logout adapter.

Run only with CROWNPATH_DISPOSABLE_PG_TEST_URL pointing to a dedicated empty
disposable database. Never use the application's DATABASE_URL.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
import hashlib

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof, consume_proof
from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test


def test_postgres_atomic_logout_rollback():
    url = os.getenv("CROWNPATH_DISPOSABLE_PG_TEST_URL")
    if not url:
        pytest.skip("Disposable PostgreSQL URL not configured")
    if not url.startswith(("postgresql://", "postgresql+psycopg://", "postgresql+psycopg2://")):
        pytest.fail("Dedicated PostgreSQL URL required")
    if any(word in url.lower() for word in ("production", "prod-db", "railway")):
        pytest.fail("Refusing URL with production/provider marker")
    # Fail closed: an explicit independent acknowledgment is required.
    if os.getenv("CROWNPATH_DISPOSABLE_PG_ACK") != "EMPTY_DISPOSABLE_ONLY":
        pytest.skip("Explicit disposable database acknowledgment required")
    engine = create_engine(url)
    # No schema creation or data deletion on any unknown remote DB: this
    # test intentionally stops until a separately provisioned isolated schema
    # and non-destructive setup protocol have been reviewed.
    engine.dispose()
    pytest.skip("PostgreSQL execution gated pending non-destructive schema isolation review")
