"""Session-aware proof consumption denies wrong identities and expired sessions.

Uses synthetic rows and a disposable SQLite database only.
"""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_session_aware_consume_test import consume_with_active_session_test


def test_session_aware_proof_denies_mismatch_and_expiry(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'session_boundary.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="boundary@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="EXPIRED-SESSION", user_id="owner",
                             token_hash=hashlib.sha256(b"expired-jti").hexdigest(),
                             token_type="SESSION", expires_at=now - timedelta(seconds=1),
                             created_at=now - timedelta(minutes=10)))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="expired-jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        assert not consume_with_active_session_test(
            engine, token=proof, user_id="owner", session_id="expired-jti", now=now)
        assert not consume_with_active_session_test(
            engine, token=proof, user_id="other-owner", session_id="expired-jti", now=now)
        assert not consume_with_active_session_test(
            engine, token=proof, user_id="owner", session_id="wrong-jti", now=now)
        assert not consume_with_active_session_test(
            engine, token="", user_id="owner", session_id="expired-jti", now=now)
    finally:
        engine.dispose()
