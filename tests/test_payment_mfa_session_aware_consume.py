"""Isolated session-aware proof consumption regression checks."""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuthToken
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_session_aware_consume_test import consume_with_active_session_test
from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test


def test_active_session_required_for_payment_proof(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'active_session_proof.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="session-proof@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="ACTIVE-PROOF", user_id="owner",
                             token_hash=hashlib.sha256(b"session-jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        first = issue_verified_proof(engine, user_id="owner", session_id="session-jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        assert consume_with_active_session_test(
            engine, token=first, user_id="owner", session_id="session-jti", now=now)
        assert not consume_with_active_session_test(
            engine, token=first, user_id="owner", session_id="session-jti", now=now)
        second = issue_verified_proof(engine, user_id="owner", session_id="session-jti",
                                      now=int(now.timestamp()), ttl_seconds=120)
        assert revoke_session_and_proofs_test(
            engine, user_id="owner", session_id="session-jti", now=now)
        assert not consume_with_active_session_test(
            engine, token=second, user_id="owner", session_id="session-jti", now=now)
    finally:
        engine.dispose()
