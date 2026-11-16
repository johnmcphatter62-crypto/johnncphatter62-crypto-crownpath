"""Concurrent consume-vs-logout test on isolated file-backed SQLite.

SQLite serializes competing writers. Whichever operation commits first may
win; if logout wins, the proof must not subsequently be consumable.
"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuthToken
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof, consume_proof
from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test


def test_competing_logout_and_proof_consume(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}", connect_args={"timeout": 15})
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="concurrent@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="CONCURRENT", user_id="owner",
                             token_hash=hashlib.sha256(b"concurrent-jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="concurrent-jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        gate = Barrier(2)

        def logout():
            gate.wait()
            return revoke_session_and_proofs_test(
                engine, user_id="owner", session_id="concurrent-jti", now=now)

        def consume():
            gate.wait()
            return consume_proof(
                engine, token=proof, user_id="owner",
                session_id="concurrent-jti", now=int(now.timestamp()) + 1)

        with ThreadPoolExecutor(max_workers=2) as pool:
            logout_future = pool.submit(logout)
            consume_future = pool.submit(consume)
            assert logout_future.result(timeout=20)
            consume_future.result(timeout=20)
        assert not consume_proof(engine, token=proof, user_id="owner",
                                 session_id="concurrent-jti", now=int(now.timestamp()) + 2)
        with Session(engine) as db:
            assert db.get(AuthToken, "CONCURRENT").used_at is not None
    finally:
        engine.dispose()
