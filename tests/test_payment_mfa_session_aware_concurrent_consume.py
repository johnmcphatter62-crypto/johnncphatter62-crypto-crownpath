"""Competing attempts to consume one session-bound payment proof.

Uses synthetic data and disposable file-backed SQLite only. The atomic SQL
UPDATE must allow at most one consumer to succeed.
"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuthToken
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_session_aware_consume_test import consume_with_active_session_test


def test_two_simultaneous_consumers_have_one_winner(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'two_consumers.db'}", connect_args={"timeout": 15})
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="two-consumers@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="TWO-CONSUMERS", user_id="owner",
                             token_hash=hashlib.sha256(b"consumer-jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="consumer-jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        gate = Barrier(2)

        def consume():
            gate.wait()
            return consume_with_active_session_test(
                engine, token=proof, user_id="owner", session_id="consumer-jti", now=now)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(consume)
            second = pool.submit(consume)
            assert sorted([first.result(timeout=20), second.result(timeout=20)]) == [False, True]
    finally:
        engine.dispose()
