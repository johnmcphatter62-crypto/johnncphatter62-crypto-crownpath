"""Negative authorization tests for isolated HMAC payment-proof consumption."""
import hashlib
import hmac
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_hmac_session_consume_test import consume_hmac_session_proof_test


@pytest.mark.parametrize("role,active,mfa_enabled", [
    ("OWNER", False, True),
    ("LEARNER", True, True),
    ("OWNER", True, False),
])
def test_invalid_owner_state_cannot_consume_proof(tmp_path, role, active, mfa_enabled):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'owner_gate.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        secret = "synthetic-secret"
        session_id = "synthetic-session"
        token_hash = hmac.new(secret.encode(), f"session:{session_id}".encode(),
                              hashlib.sha256).hexdigest()
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Owner", email="owner@example.invalid",
                        password_hash="synthetic", role=role, active=active,
                        mfa_enabled=mfa_enabled))
            db.add(AuthToken(token_id="SESSION", user_id="owner",
                             token_hash=token_hash, token_type="SESSION",
                             expires_at=now + timedelta(minutes=5),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner",
                                     session_id=session_id, now=int(now.timestamp()))
        assert not consume_hmac_session_proof_test(
            engine, token=proof, user_id="owner", session_id=session_id,
            secret=secret, now=now)
        # Denial must not burn a proof. Restoring authorization allows one use.
        with Session(engine) as db:
            user = db.get(User, "owner")
            user.role = "OWNER"
            user.active = True
            user.mfa_enabled = True
            db.commit()
        assert consume_hmac_session_proof_test(
            engine, token=proof, user_id="owner", session_id=session_id,
            secret=secret, now=now)
        assert not consume_hmac_session_proof_test(
            engine, token=proof, user_id="owner", session_id=session_id,
            secret=secret, now=now)
    finally:
        engine.dispose()
