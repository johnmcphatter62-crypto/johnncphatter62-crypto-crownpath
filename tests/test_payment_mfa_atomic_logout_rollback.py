"""Isolated rollback check for the experimental atomic logout adapter."""
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof, consume_proof
from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test


def test_rollback_then_success(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'rollback.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="rollback@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="ROLLBACK", user_id="owner",
                             token_hash=hashlib.sha256(b"jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        with pytest.raises(RuntimeError):
            revoke_session_and_proofs_test(
                engine, user_id="owner", session_id="jti", now=now,
                fail_after_session_update=True)
        with Session(engine) as db:
            assert db.get(AuthToken, "ROLLBACK").used_at is None
        assert revoke_session_and_proofs_test(engine, user_id="owner", session_id="jti", now=now)
        assert not consume_proof(engine, token=proof, user_id="owner",
                                 session_id="jti", now=int(now.timestamp()) + 1)
    finally:
        engine.dispose()
