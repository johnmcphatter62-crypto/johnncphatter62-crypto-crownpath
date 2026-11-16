"""Deterministic competing-request boundary on disposable SQLite.

This checks the ordered case where logout commits before proof consumption.
It does not claim to prove every possible concurrent interleaving.
"""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuthToken
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof, consume_proof
from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test


def test_logout_commit_precedes_competing_proof_use(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'ordered_race.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="ordered-race@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="RACE", user_id="owner",
                             token_hash=hashlib.sha256(b"race-jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="race-jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        assert revoke_session_and_proofs_test(engine, user_id="owner",
                                               session_id="race-jti", now=now)
        assert not consume_proof(engine, token=proof, user_id="owner",
                                 session_id="race-jti", now=int(now.timestamp()) + 1)
        assert not revoke_session_and_proofs_test(engine, user_id="owner",
                                                   session_id="race-jti", now=now)
    finally:
        engine.dispose()
