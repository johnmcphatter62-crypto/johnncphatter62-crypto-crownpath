"""Two concurrent logout requests must not both revoke the same session.

Disposable SQLite only; no production route or credential is involved.
"""
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof, consume_proof
from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test


def test_simultaneous_logout_has_one_winner(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'double_logout.db'}", connect_args={"timeout": 15})
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            db.add(User(user_id="owner", name="Test", email="double-logout@example.invalid",
                        password_hash="synthetic", role="OWNER", active=True, mfa_enabled=True))
            db.add(AuthToken(token_id="DOUBLE-LOGOUT", user_id="owner",
                             token_hash=hashlib.sha256(b"double-jti").hexdigest(),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10),
                             created_at=now))
            db.commit()
        proof = issue_verified_proof(engine, user_id="owner", session_id="double-jti",
                                     now=int(now.timestamp()), ttl_seconds=120)
        gate = Barrier(2)

        def logout():
            gate.wait()
            return revoke_session_and_proofs_test(
                engine, user_id="owner", session_id="double-jti", now=now)

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(logout)
            b = pool.submit(logout)
            assert sorted([a.result(timeout=20), b.result(timeout=20)]) == [False, True]
        assert not consume_proof(engine, token=proof, user_id="owner",
                                 session_id="double-jti", now=int(now.timestamp()) + 1)
    finally:
        engine.dispose()
