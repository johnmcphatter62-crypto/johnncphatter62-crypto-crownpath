"""Disposable SQLite tests for session-bound database proof contract."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof,
)

def test_session_binding_expiry_and_one_use(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'proofs.db'}")
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="session-a", now=100)
        assert not consume_proof(engine, token=token, user_id="owner", session_id="session-b", now=101)
        assert not consume_proof(engine, token=token, user_id="other", session_id="session-a", now=101)
        assert consume_proof(engine, token=token, user_id="owner", session_id="session-a", now=101)
        assert not consume_proof(engine, token=token, user_id="owner", session_id="session-a", now=101)
        expired = issue_verified_proof(engine, user_id="owner", session_id="session-a", now=100)
        assert not consume_proof(engine, token=expired, user_id="owner", session_id="session-a", now=220)
    finally:
        engine.dispose()

def test_concurrent_database_consume_exactly_once(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'proofs.db'}", connect_args={"timeout": 20})
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="session-a", now=100)
        barrier = Barrier(8)
        def attempt(_):
            barrier.wait(timeout=10)
            return consume_proof(engine, token=token, user_id="owner", session_id="session-a", now=101)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(attempt, range(8)))
        assert results.count(True) == 1
    finally:
        engine.dispose()
