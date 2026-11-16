"""Lock-timeout rollback checks on a fresh disposable PostgreSQL schema."""
from datetime import datetime, timezone

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


@pytest.mark.parametrize("operation", ["logout", "consume"])
@pytest.mark.parametrize("blocked_row", ["session", "proof"])
def test_postgres_lock_timeout_rolls_back_and_can_retry(
    isolated_logout_engine, monkeypatch, operation, blocked_row,
):
    import jwt
    from crownpath import auth
    from crownpath.models import AuthToken, User
    from crownpath.payment_mfa_db_proof import issue_verified_proof
    from crownpath.payment_mfa_atomic_logout_test_adapter import revoke_session_and_proofs_test
    from crownpath.payment_mfa_session_aware_consume_test import consume_with_active_session_test

    engine = isolated_logout_engine
    monkeypatch.setattr(auth, "session", sessionmaker(bind=engine))
    with Session(engine) as db:
        db.add(User(user_id="timeout-owner", name="Synthetic Timeout Owner",
                    email="timeout-owner@example.invalid", password_hash="synthetic-only",
                    role="OWNER", active=True, mfa_enabled=True))
        db.commit()
    token = auth.create_access_token("timeout-owner")
    untouched = auth.create_access_token("timeout-owner")
    assert auth.decode_access_token(token) == "timeout-owner"
    jti = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])["jti"]
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    proof = issue_verified_proof(engine, user_id="timeout-owner", session_id=jti, now=timestamp)

    def states():
        with engine.connect() as conn:
            session_state = conn.scalar(sa.select(AuthToken.used_at).where(
                AuthToken.token_hash == auth._hash_session_id(jti),
            ))
            proof_state = conn.scalar(sa.text(
                "SELECT used_at FROM payment_mfa_proofs_test WHERE session_id=:sid"
            ), {"sid": jti})
        return session_state, proof_state

    def operate(target):
        if operation == "logout":
            return revoke_session_and_proofs_test(
                target, user_id="timeout-owner", session_id=jti, now=now,
            )
        return consume_with_active_session_test(
            target, token=proof, user_id="timeout-owner", session_id=jti, now=now,
        )

    before = states()
    assert before == (None, None)
    with engine.connect() as conn:
        schema = conn.scalar(sa.text("SELECT current_schema()"))
    # Reuse only the verified disposable target, with a short bounded timeout.
    worker = sa.create_engine(engine.url, connect_args={
        "connect_timeout": 5,
        "options": f"-csearch_path={schema} -clock_timeout=150 -cstatement_timeout=2000",
    })
    blocker = engine.connect()
    transaction = blocker.begin()
    try:
        if blocked_row == "session":
            blocker.execute(sa.select(AuthToken.token_id).where(
                AuthToken.token_hash == auth._hash_session_id(jti),
            ).with_for_update()).scalar_one()
        else:
            blocker.execute(sa.text(
                "SELECT proof_hash FROM payment_mfa_proofs_test "
                "WHERE session_id=:sid FOR UPDATE"
            ), {"sid": jti}).scalar_one()
        with pytest.raises(sa.exc.OperationalError) as error:
            operate(worker)
        assert error.value.orig.sqlstate == "55P03", "Expected PostgreSQL lock timeout"
        # In the proof-blocked logout case this also verifies that the earlier
        # session UPDATE was rolled back when the second UPDATE timed out.
        assert states() == before
        assert auth.decode_access_token(token) == "timeout-owner"
        assert auth.decode_access_token(untouched) == "timeout-owner"
    finally:
        transaction.rollback()
        blocker.close()
        worker.dispose()

    # An explicit retry after releasing the blocker must work once, then deny.
    assert operate(engine) is True
    assert operate(engine) is False
    if operation == "logout":
        assert states() == (now, timestamp)
        assert auth.decode_access_token(token) is None
    else:
        assert states() == (None, timestamp)
        assert auth.decode_access_token(token) == "timeout-owner"
        assert revoke_session_and_proofs_test(
            engine, user_id="timeout-owner", session_id=jti, now=now,
        )
        assert auth.decode_access_token(token) is None
    assert not consume_with_active_session_test(
        engine, token=proof, user_id="timeout-owner", session_id=jti, now=now,
    )
    assert auth.decode_access_token(untouched) == "timeout-owner"
