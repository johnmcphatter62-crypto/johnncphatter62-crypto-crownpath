"""Integration tests for session-bound MFA proof prototype on disposable CI PostgreSQL.

Only the CI database at localhost:5432/crownpath_ci is permitted. This test
creates and drops its own table and never touches production credentials.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof,
)

def _ci_engine():
    url = os.environ.get("CROWNPATH_DATABASE_URL", "")
    if "localhost:5432/crownpath_ci" not in url:
        pytest.skip("Requires disposable localhost crownpath_ci PostgreSQL.")
    return sa.create_engine(url, pool_size=10, max_overflow=0)

def test_postgres_session_bound_atomic_proof():
    engine = _ci_engine()
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS payment_mfa_proofs_test"))
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        assert not consume_proof(engine, token=token, user_id="owner", session_id="s2", now=101)
        assert not consume_proof(engine, token=token, user_id="other", session_id="s1", now=101)
        barrier = Barrier(8)

        def attempt(_):
            barrier.wait(timeout=15)
            return consume_proof(engine, token=token, user_id="owner", session_id="s1", now=101)

        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(attempt, range(8)))
        assert outcomes.count(True) == 1
        assert outcomes.count(False) == 7
        assert not consume_proof(engine, token=token, user_id="owner", session_id="s1", now=102)
        expired = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        assert not consume_proof(engine, token=expired, user_id="owner", session_id="s1", now=220)
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text("DROP TABLE IF EXISTS payment_mfa_proofs_test"))
        engine.dispose()
