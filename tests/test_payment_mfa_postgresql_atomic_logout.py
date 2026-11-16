"""Opt-in atomic logout proof on a fresh disposable PostgreSQL database.

The dedicated URL must never refer to production or restored real data.
No application route is changed by this test.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from crownpath.payment_mfa_pg_isolation_guard import assert_isolated_pg_target


@pytest.fixture
def isolated_logout_engine():
    raw = os.environ.get("CROWNPATH_ATOMIC_LOGOUT_POSTGRES_URL")
    if not raw:
        pytest.skip("Dedicated disposable PostgreSQL logout URL required")
    url = make_url(raw)
    if (url.drivername != "postgresql+psycopg"
            or url.host not in ("localhost", "127.0.0.1", "::1")
            or url.query):
        pytest.fail("Only a direct loopback psycopg URL without query overrides is allowed")
    if os.environ.get("CROWNPATH_ENV") != "staging":
        pytest.fail("Staging required")
    schema = "crownpath_test_" + uuid.uuid4().hex
    assert_isolated_pg_target(
        database_name=url.database, schema_name=schema,
        acknowledged=os.environ.get("CROWNPATH_TEST_DB_DISPOSABLE") == "YES",
    )
    admin = sa.create_engine(url, connect_args={"connect_timeout": 5})
    engine = None
    created = False
    try:
        with admin.begin() as conn:
            assert conn.scalar(sa.text("SELECT current_database()")) == url.database
            assert conn.scalar(sa.text(
                "SELECT pg_get_userbyid(datdba) = current_user "
                "FROM pg_database WHERE datname = current_database()"
            )) is True
            # Reject existing user relations before creating any test objects.
            assert conn.scalar(sa.text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
                "AND n.nspname NOT LIKE 'pg_toast%' AND n.nspname NOT LIKE 'pg_temp_%'"
            )) == 0
            conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
        created = True
        engine = sa.create_engine(url, connect_args={
            "connect_timeout": 5,
            "options": f"-csearch_path={schema} -clock_timeout=5000 -cstatement_timeout=10000",
        })
        from crownpath.models import AuthToken, User
        from crownpath.payment_mfa_db_proof import create_test_schema
        with engine.begin() as conn:
            assert conn.scalar(sa.text("SELECT current_schema()")) == schema
        User.__table__.create(engine)
        AuthToken.__table__.create(engine)
        create_test_schema(engine)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        if created:
            with admin.begin() as conn:
                conn.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_postgres_atomic_logout_rollback_and_session_isolation(isolated_logout_engine, monkeypatch):
    from crownpath.models import AuthToken, User
    from crownpath.payment_mfa_db_proof import issue_verified_proof, consume_proof
    from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test

    from crownpath.auth import _hash_session_id

    engine = isolated_logout_engine
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    scopes = [("owner", "target"), ("owner", "other-session"), ("other-owner", "other-user")]
    with Session(engine) as db:
        for uid in ("owner", "other-owner"):
            db.add(User(user_id=uid, name="Synthetic Owner", email=f"{uid}@example.invalid",
                        password_hash="synthetic-only", role="OWNER", active=True, mfa_enabled=True))
        db.flush()
        for uid, sid in scopes:
            db.add(AuthToken(token_id=sid, user_id=uid,
                             token_hash=_hash_session_id(sid),
                             token_type="SESSION", expires_at=now + timedelta(minutes=10), created_at=now))
        db.commit()
    proofs = {sid: issue_verified_proof(engine, user_id=uid, session_id=sid, now=timestamp)
              for uid, sid in scopes}

    def states():
        with engine.connect() as conn:
            sessions = dict(conn.execute(sa.text("SELECT token_id, used_at FROM auth_tokens")).all())
            tokens = dict(conn.execute(sa.text("SELECT session_id, used_at FROM payment_mfa_proofs_test")).all())
        return sessions, tokens

    before = states()
    with pytest.raises(RuntimeError, match="synthetic failure"):
        revoke_session_and_proofs_test(engine, user_id="owner", session_id="target", now=now,
                                       fail_after_session_update=True)
    assert states() == before

    # Also force a real PostgreSQL statement failure during proof revocation.
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE payment_mfa_proofs_test ADD CONSTRAINT reject_revocation CHECK (used_at IS NULL)"))
    with pytest.raises(sa.exc.IntegrityError):
        revoke_session_and_proofs_test(engine, user_id="owner", session_id="target", now=now)
    assert states() == before
    with engine.begin() as conn:
        conn.execute(sa.text("ALTER TABLE payment_mfa_proofs_test DROP CONSTRAINT reject_revocation"))

    assert revoke_session_and_proofs_test(engine, user_id="owner", session_id="target", now=now)
    sessions, tokens = states()
    assert sessions["target"] == now
    assert tokens["target"] == timestamp
    for sid in ("other-session", "other-user"):
        assert sessions[sid] is None
        assert tokens[sid] is None
    assert not consume_proof(engine, token=proofs["target"], user_id="owner", session_id="target", now=timestamp + 1)
    assert not revoke_session_and_proofs_test(engine, user_id="owner", session_id="target", now=now)

    # Use the real issuer and decoder, bound only to this disposable schema.
    import jwt
    from sqlalchemy.orm import sessionmaker
    from crownpath import auth
    monkeypatch.setattr(auth, "session", sessionmaker(bind=engine))
    issued = auth.create_access_token("owner")
    assert auth.decode_access_token(issued) == "owner"
    claims = jwt.decode(issued, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
    real_jti = claims["jti"]
    issued_now = datetime.now(timezone.utc)
    issued_timestamp = int(issued_now.timestamp())
    issued_proof = issue_verified_proof(
        engine, user_id="owner", session_id=real_jti, now=issued_timestamp,
    )
    assert not revoke_session_and_proofs_test(
        engine, user_id="other-owner", session_id=real_jti, now=issued_now,
    )
    with pytest.raises(RuntimeError, match="synthetic failure"):
        revoke_session_and_proofs_test(
            engine, user_id="owner", session_id=real_jti, now=issued_now,
            fail_after_session_update=True,
        )
    assert auth.decode_access_token(issued) == "owner"
    with engine.connect() as conn:
        assert conn.scalar(sa.text(
            "SELECT used_at FROM payment_mfa_proofs_test WHERE session_id=:sid"
        ), {"sid": real_jti}) is None
    assert revoke_session_and_proofs_test(
        engine, user_id="owner", session_id=real_jti, now=issued_now,
    )
    assert auth.decode_access_token(issued) is None
    assert not consume_proof(
        engine, token=issued_proof, user_id="owner", session_id=real_jti,
        now=issued_timestamp + 1,
    )
    assert not revoke_session_and_proofs_test(
        engine, user_id="owner", session_id=real_jti, now=issued_now,
    )

    # Plain SHA fixtures must not be accepted as real sessions.
    import hashlib
    legacy_jti = "synthetic-plain-hash-only"
    with Session(engine) as db:
        db.add(AuthToken(
            token_id="plain-hash-only", user_id="owner",
            token_hash=hashlib.sha256(legacy_jti.encode()).hexdigest(),
            token_type="SESSION", expires_at=issued_now + timedelta(minutes=10),
            created_at=issued_now,
        ))
        db.commit()
    assert not revoke_session_and_proofs_test(
        engine, user_id="owner", session_id=legacy_jti, now=issued_now,
    )
    with Session(engine) as db:
        assert db.get(AuthToken, "plain-hash-only").used_at is None
