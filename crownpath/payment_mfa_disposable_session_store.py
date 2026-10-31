"""Disposable SQLite session row validation for isolated payment MFA tests.

This intentionally models the authoritative hashed session row without using
application production database connections or credentials.
"""
import hashlib
import sqlalchemy as sa


def create_session_test_schema(engine):
    with engine.begin() as conn:
        conn.execute(sa.text("""
            CREATE TABLE IF NOT EXISTS payment_session_rows_test (
                user_id VARCHAR(128) NOT NULL,
                session_hash VARCHAR(64) NOT NULL,
                active BOOLEAN NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, session_hash)
            )
        """))


def session_hash(session_id):
    return hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def add_test_session(engine, *, user_id, session_id):
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO payment_session_rows_test
                (user_id, session_hash, active, revoked)
            VALUES (:user_id, :session_hash, 1, 0)
        """), {"user_id": user_id, "session_hash": session_hash(session_id)})


def is_active_test_session(engine, user_id, session_id):
    if not all(isinstance(x, str) and x.strip() for x in (user_id, session_id)):
        return False
    with engine.connect() as conn:
        row = conn.execute(sa.text("""
            SELECT active, revoked FROM payment_session_rows_test
            WHERE user_id=:user_id AND session_hash=:session_hash
        """), {"user_id": user_id, "session_hash": session_hash(session_id)}).first()
    return bool(row and row.active and not row.revoked)


def revoke_test_session(engine, *, user_id, session_id):
    with engine.begin() as conn:
        result = conn.execute(sa.text("""
            UPDATE payment_session_rows_test SET revoked=1
            WHERE user_id=:user_id AND session_hash=:session_hash AND revoked=0
        """), {"user_id": user_id, "session_hash": session_hash(session_id)})
    return result.rowcount == 1
