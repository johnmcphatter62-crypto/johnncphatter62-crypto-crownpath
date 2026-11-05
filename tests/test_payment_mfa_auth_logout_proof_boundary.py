"""Logout/proof boundary with actual CrownPath auth functions, disposable DB only.

This verifies sequential logout + explicit proof revocation, NOT atomic
coordination; production logout is not yet wired to payment-proof revocation.
"""
import jwt
import sqlalchemy as sa
from sqlalchemy.orm import Session

import crownpath.auth as auth
from crownpath.db_engine import Base
from crownpath.models import User
from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof,
    revoke_session_proofs,
)


def test_logout_then_revoke_payment_proof(monkeypatch, tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'logout_proof.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        with Session(engine) as db:
            db.add(User(
                user_id="owner", name="Synthetic Owner",
                email="logout-proof@example.invalid",
                password_hash="test-only", role="OWNER",
                active=True, mfa_enabled=True,
            ))
            db.commit()
        monkeypatch.setattr(auth, "session", lambda: Session(engine))
        monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-logout-secret")
        session_token = auth.create_access_token("owner")
        session_id = jwt.decode(
            session_token, "synthetic-logout-secret", algorithms=["HS256"]
        )["jti"]
        proof = issue_verified_proof(
            engine, user_id="owner", session_id=session_id, now=100, ttl_seconds=120
        )
        assert auth.decode_access_token(session_token) == "owner"
        assert auth.revoke_access_token(session_token) is True
        assert auth.decode_access_token(session_token) is None
        assert revoke_session_proofs(
            engine, user_id="owner", session_id=session_id, now=101
        ) == 1
        assert not consume_proof(
            engine, token=proof, user_id="owner", session_id=session_id, now=102
        )
    finally:
        engine.dispose()
