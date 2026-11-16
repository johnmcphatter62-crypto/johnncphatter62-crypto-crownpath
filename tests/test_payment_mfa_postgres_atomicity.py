"""PostgreSQL atomic payment MFA proof test, restricted to disposable CI DB.

No production connection, payment provider, or credentials are used here.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
import sqlalchemy as sa

def _ci_url():
    url = os.environ.get("CROWNPATH_DATABASE_URL", "")
    if "localhost:5432/crownpath_ci" not in url:
        pytest.skip("Restricted to disposable localhost PostgreSQL crownpath_ci.")
    return url

def test_postgres_single_use_across_connections():
    engine = sa.create_engine(_ci_url(), pool_size=10, max_overflow=0)
    table = "payment_mfa_atomicity_test"
    try:
        with engine.begin() as conn:
            conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(sa.text(f"CREATE TABLE {table} (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, purpose TEXT NOT NULL, expires_at BIGINT NOT NULL, used_at BIGINT)"))
            conn.execute(sa.text(f"INSERT INTO {table} VALUES ('synthetic-hash','owner-1','payments.configure',500,NULL)"))

        barrier = Barrier(8)

        def consume(_):
            barrier.wait(timeout=15)
            with engine.begin() as conn:
                result = conn.execute(sa.text(f"UPDATE {table} SET used_at=100 WHERE token_hash='synthetic-hash' AND user_id='owner-1' AND purpose='payments.configure' AND used_at IS NULL AND expires_at>100"))
                return result.rowcount == 1

        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(consume, range(8)))
        assert outcomes.count(True) == 1
        assert outcomes.count(False) == 7
    finally:
        with engine.begin() as conn:
            conn.execute(sa.text(f"DROP TABLE IF EXISTS {table}"))
        engine.dispose()
