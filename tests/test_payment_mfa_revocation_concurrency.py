"""Disposable SQLite race tests for payment MFA proof revocation.

No live sessions, secrets, or production databases are used.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof, revoke_session_proofs,
)

def test_concurrent_revocations_are_idempotent(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'concurrent_revoke.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        barrier = Barrier(6)
        def revoke(_):
            barrier.wait(timeout=15)
            return revoke_session_proofs(engine, user_id="owner", session_id="s1", now=101)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(revoke, range(6)))
        assert sorted(results) == [0, 0, 0, 0, 0, 1]
        assert not consume_proof(engine, token=proof, user_id="owner", session_id="s1", now=102)
    finally:
        engine.dispose()

def test_revoked_proof_remains_invalid_under_concurrent_consumption(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'revoked_consume.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        assert revoke_session_proofs(engine, user_id="owner", session_id="s1", now=101) == 1
        barrier = Barrier(6)
        def consume(_):
            barrier.wait(timeout=15)
            return consume_proof(engine, token=proof, user_id="owner", session_id="s1", now=102)
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(consume, range(6)))
        assert results == [False] * 6
    finally:
        engine.dispose()
