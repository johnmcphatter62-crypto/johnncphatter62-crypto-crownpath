"""Expired payment proof must fail even with an otherwise active session."""
import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuthToken
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_session_aware_consume_test import consume_with_active_session_test


def test_expired_proof_rejected_with_active_session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'expired_proof.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="expired-proof@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="PROOF-EXPIRY", user_id="owner",
                             token_hash=hashlib.sha256(b"expiry-jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="expiry-jti",
                                     now=int(now.timestamp()) - 180, ttl_seconds=120)
        assert not consume_with_active_session_test(
            engine, token=proof, user_id="owner", session_id="expiry-jti", now=now)
    finally:
        engine.dispose()
