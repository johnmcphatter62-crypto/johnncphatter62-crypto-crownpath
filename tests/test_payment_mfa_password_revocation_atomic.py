"""Disposable SQLite regression tests for coordinated password/proof revocation."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from crownpath.db_engine import Base
from crownpath.models import AuthToken, User
from crownpath.payment_mfa_db_proof import create_test_schema, issue_verified_proof, consume_proof
from crownpath.payment_mfa_password_revocation_test_adapter import revoke_password_sessions_and_proofs_test

SECRET = "synthetic-session-secret"


def session_hash(jti):
    return hmac.new(SECRET.encode(), f"session:{jti}".encode(), hashlib.sha256).hexdigest()


@pytest.mark.parametrize("fail_midway", [False, True])
def test_password_change_is_atomic_and_owner_scoped(tmp_path, fail_midway):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'atomic_password.db'}")
    try:
        Base.metadata.create_all(engine)
        create_test_schema(engine)
        now = datetime.now(timezone.utc)
        with Session(engine) as db:
            for uid in ("owner-a", "owner-b"):
                db.add(User(user_id=uid, name=uid, email=f"{uid}@example.invalid",
                            password_hash="before", role="OWNER", active=True, mfa_enabled=True))
            for tid, uid, jti in (
                ("A1", "owner-a", "session-a1"),
                ("A2", "owner-a", "session-a2"),
                ("B1", "owner-b", "session-b1"),
            ):
                db.add(AuthToken(token_id=tid, user_id=uid, token_hash=session_hash(jti),
                                 token_type="SESSION", expires_at=now + timedelta(minutes=10),
                                 created_at=now))
            db.commit()
        timestamp = int(now.timestamp())
        cases = [("owner-a", "session-a1"), ("owner-a", "session-a2"),
                 ("owner-b", "session-b1")]
        proofs = [issue_verified_proof(engine, user_id=uid, session_id=jti, now=timestamp)
                  for uid, jti in cases]
        if fail_midway:
            with pytest.raises(RuntimeError, match="synthetic failure"):
                revoke_password_sessions_and_proofs_test(
                    engine, user_id="owner-a", new_hash="after",
                    now=now, fail_midway=True)
        else:
            assert revoke_password_sessions_and_proofs_test(
                engine, user_id="owner-a", new_hash="after", now=now)
        with Session(engine) as db:
            assert db.get(User, "owner-a").password_hash == (
                "before" if fail_midway else "after")
            assert (db.get(AuthToken, "A1").used_at is None) == fail_midway
            assert (db.get(AuthToken, "A2").used_at is None) == fail_midway
            assert db.get(User, "owner-b").password_hash == "before"
            assert db.get(AuthToken, "B1").used_at is None
        for index, (uid, jti) in enumerate(cases):
            expected = fail_midway if uid == "owner-a" else True
            assert consume_proof(engine, token=proofs[index], user_id=uid,
                                 session_id=jti, now=timestamp + 1) is expected
    finally:
        engine.dispose()
