"""SQLite-only race: Owner role downgrade versus payment proof consumption.

This test covers the experimental database helper, not production payments.
"""
import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof
from crownpath.payment_mfa_hmac_session_consume_test import consume_hmac_session_proof_test


def test_owner_role_downgrade_competes_with_payment_proof(tmp_path):
    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'role_race.db'}", connect_args={"timeout": 20})
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        secret, session_id = "synthetic-secret", "synthetic-session"
        token_hash = hmac.new(secret.encode(), f"session:{session_id}".encode(),
                              hashlib.sha256).hexdigest()
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Owner", email="owner@example.invalid",
                        password_hash="synthetic", role="OWNER",
                        active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="SESSION", user_id="owner",
                             token_hash=token_hash, token_type="SESSION",
                             expires_at=now + timedelta(minutes=5),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner",
                                     session_id=session_id, now=int(now.timestamp()))
        barrier = Barrier(2)

        def downgrade():
            barrier.wait(timeout=15)
            with Session(engine) as db:
                with db.begin():
                    db.execute(sa.update(User).where(User.user_id == "owner")
                               .values(role="HOME_CARE"))
            return True

        def consume():
            barrier.wait(timeout=15)
            return consume_hmac_session_proof_test(
                engine, token=proof, user_id="owner", session_id=session_id,
                secret=secret, now=now)

        with ThreadPoolExecutor(max_workers=2) as pool:
            downgraded = pool.submit(downgrade)
            consumed = pool.submit(consume)
            assert downgraded.result(timeout=25)
            consumed.result(timeout=25)
        with Session(engine) as db:
            assert db.get(User, "owner").role == "HOME_CARE"
        assert not consume_hmac_session_proof_test(
            engine, token=proof, user_id="owner", session_id=session_id,
            secret=secret, now=now)
    finally:
        engine.dispose()
