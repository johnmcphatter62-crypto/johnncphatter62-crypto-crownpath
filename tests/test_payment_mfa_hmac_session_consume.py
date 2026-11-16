"""Isolated tests for HMAC-backed, active-session payment proof consumption."""
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


@pytest.mark.parametrize("case", ["valid", "revoked", "expired", "wrong_secret", "wrong_session"])
def test_payment_proof_requires_live_matching_hmac_session(tmp_path, case):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'proof.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        secret = "synthetic-secret"
        jti = "session-one"
        digest = hmac.new(secret.encode(), f"session:{jti}".encode(),
                          hashlib.sha256).hexdigest()
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Owner", email="owner@example.invalid",
                        password_hash="synthetic", role="OWNER",
                        active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="SESSION-1", user_id="owner",
                             token_hash=digest, token_type="SESSION",
                             created_at=now,
                             expires_at=now - timedelta(seconds=1) if case == "expired"
                                        else now + timedelta(minutes=5),
                             used_at=now if case == "revoked" else None))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id=jti,
                                     now=int(now.timestamp()), ttl_seconds=120)
        kwargs = dict(token=proof, user_id="owner", session_id=jti,
                      secret=secret, now=now)
        if case == "wrong_secret":
            kwargs["secret"] = "different-secret"
        if case == "wrong_session":
            kwargs["session_id"] = "different-session"
        success = consume_hmac_session_proof_test(engine, **kwargs)
        assert success is (case == "valid")
        assert not consume_hmac_session_proof_test(engine, **kwargs)
    finally:
        engine.dispose()
