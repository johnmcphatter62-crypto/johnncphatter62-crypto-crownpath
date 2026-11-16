"""Concurrent password-change revocation versus proof use, disposable SQLite only.

A proof may be consumed before revocation wins. No proof may be consumed
after the password-change transaction has committed. No provider calls.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
import hashlib
import hmac

import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import User, AuthToken
from crownpath.payment_mfa_db_proof import (
    create_test_schema, issue_verified_proof, consume_proof,
)
from crownpath.payment_mfa_password_revocation_test_adapter import (
    revoke_password_sessions_and_proofs_test,
)


def test_password_change_competes_with_proof_consumption(tmp_path):
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'password_race.db'}",
        connect_args={"timeout": 20},
    )
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        jti = "synthetic-jti"
        digest = hmac.new(b"synthetic-key", f"session:{jti}".encode(),
                          hashlib.sha256).hexdigest()
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Owner", email="owner@example.invalid",
                        password_hash="before", role="OWNER",
                        active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="SESSION", user_id="owner",
                             token_hash=digest, token_type="SESSION",
                             expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        timestamp = int(now.timestamp())
        proof = issue_verified_proof(
            engine, user_id="owner", session_id=jti, now=timestamp)
        gate = Barrier(2)

        def change_password():
            gate.wait(timeout=15)
            return revoke_password_sessions_and_proofs_test(
                engine, user_id="owner", new_hash="after", now=now)

        def consume():
            gate.wait(timeout=15)
            return consume_proof(engine, token=proof, user_id="owner",
                                 session_id=jti, now=timestamp + 1)

        with ThreadPoolExecutor(max_workers=2) as pool:
            changed = pool.submit(change_password)
            consumed = pool.submit(consume)
            assert changed.result(timeout=25) is True
            consumed.result(timeout=25)

        with Session(engine) as db:
            assert db.get(User, "owner").password_hash == "after"
            assert db.get(AuthToken, "SESSION").used_at is not None
        assert not consume_proof(engine, token=proof, user_id="owner",
                                 session_id=jti, now=timestamp + 2)
    finally:
        engine.dispose()
