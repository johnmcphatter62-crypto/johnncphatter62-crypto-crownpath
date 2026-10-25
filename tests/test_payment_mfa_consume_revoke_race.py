"""Test the ordering boundary between proof consumption and revocation.

The test intentionally checks the database primitive, not actual logout.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import sqlalchemy as sa

from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof, revoke_session_proofs,
)


def test_consume_racing_revoke_has_single_terminal_state(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'race.db'}", timeout=20)
    try:
        create_test_schema(engine)
        token = issue_verified_proof(engine, user_id="owner", session_id="s1", now=100)
        barrier = Barrier(2)

        def consume():
            barrier.wait(timeout=15)
            return consume_proof(engine, token=token, user_id="owner", session_id="s1", now=101)

        def revoke():
            barrier.wait(timeout=15)
            return revoke_session_proofs(engine, user_id="owner", session_id="s1", now=101)

        with ThreadPoolExecutor(max_workers=2) as pool:
            consumed_future = pool.submit(consume)
            revoked_future = pool.submit(revoke)
            consumed = consumed_future.result()
            revoked_count = revoked_future.result()

        # The first committed UPDATE wins. Both cannot claim success.
        assert (consumed, revoked_count) in {(True, 0), (False, 1)}
        assert not consume_proof(engine, token=token, user_id="owner", session_id="s1", now=102)
    finally:
        engine.dispose()
