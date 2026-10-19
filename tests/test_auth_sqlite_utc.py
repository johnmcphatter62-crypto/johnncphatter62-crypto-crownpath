"""Isolated SQLite regression tests for CrownPath's original auth module."""
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
import uuid

_tmp = tempfile.TemporaryDirectory(prefix="crownpath-auth-sqlite-")
os.environ["CROWNPATH_ENV"] = "development"
os.environ["CROWNPATH_DATABASE_URL"] = "sqlite:///" + str(Path(_tmp.name) / "auth-test.db")
os.environ["CROWNPATH_SECRET_KEY"] = "ci-only-auth-sqlite-secret-do-not-use-in-production"

from sqlalchemy import delete, update
from crownpath.auth import (
    authenticate, consume_one_time_token, create_access_token,
    create_one_time_token, create_user, decode_access_token, revoke_access_token,
)
from crownpath.database import init_db, session
from crownpath.models import AuthToken, User

def _new_user():
    return create_user("SQLite UTC Test", f"sqlite-{uuid.uuid4().hex}@example.invalid",
                       "Strong-Test-Password-2026!", "HOME_CARE")

def _cleanup(user_id):
    db = session()
    try:
        db.execute(delete(AuthToken).where(AuthToken.user_id == user_id))
        db.execute(delete(User).where(User.user_id == user_id))
        db.commit()
    finally:
        db.close()

def setup_module(module):
    init_db()

def test_session_valid_then_revoked():
    user = _new_user()
    try:
        token = create_access_token(user["user_id"])
        assert decode_access_token(token) == user["user_id"]
        assert revoke_access_token(token)
        assert decode_access_token(token) is None
    finally:
        _cleanup(user["user_id"])

def test_database_expired_session_denied():
    user = _new_user()
    try:
        token = create_access_token(user["user_id"])
        db = session()
        try:
            db.execute(update(AuthToken).where(AuthToken.user_id == user["user_id"],
                AuthToken.token_type == "SESSION").values(
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
            db.commit()
        finally:
            db.close()
        assert decode_access_token(token) is None
    finally:
        _cleanup(user["user_id"])

def test_one_time_token_single_use_and_expiration():
    user = _new_user()
    try:
        raw = create_one_time_token(user["user_id"], "EMAIL_VERIFY", minutes=5)
        assert consume_one_time_token(raw, "EMAIL_VERIFY") == user["user_id"]
        assert consume_one_time_token(raw, "EMAIL_VERIFY") is None
        expired = create_one_time_token(user["user_id"], "PASSWORD_RESET", minutes=-1)
        assert consume_one_time_token(expired, "PASSWORD_RESET") is None
    finally:
        _cleanup(user["user_id"])

def test_lockout_blocks_authentication():
    user = _new_user()
    try:
        db = session()
        try:
            db.execute(update(User).where(User.user_id == user["user_id"]).values(
                locked_until=datetime.now(timezone.utc) + timedelta(minutes=10)))
            db.commit()
        finally:
            db.close()
        logged_in, status = authenticate(user["email"], "Strong-Test-Password-2026!")
        assert logged_in is None
        assert status == "LOCKED"
    finally:
        _cleanup(user["user_id"])


def test_utc_normalization_naive_and_offset():
    from crownpath.auth import _as_utc
    base = datetime(2026, 10, 19, 12, 0, 0)
    assert _as_utc(base) == base.replace(tzinfo=timezone.utc)
    offset = timezone(timedelta(hours=-4))
    assert _as_utc(datetime(2026, 10, 19, 8, 0, tzinfo=offset)) == base.replace(tzinfo=timezone.utc)


def test_session_expiration_boundary_existing_policy(monkeypatch):
    from crownpath import auth
    user = _new_user()
    try:
        token = create_access_token(user["user_id"])
        fixed = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
        db = session()
        try:
            db.execute(update(AuthToken).where(AuthToken.user_id == user["user_id"],
                AuthToken.token_type == "SESSION").values(expires_at=fixed))
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr(auth, "now_utc", lambda: fixed)
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        assert auth._active_session(user["user_id"], payload["jti"])
        monkeypatch.setattr(auth, "now_utc", lambda: fixed + timedelta(microseconds=1))
        assert not auth._active_session(user["user_id"], payload["jti"])
    finally:
        _cleanup(user["user_id"])


def test_lockout_expired_allows_login():
    user = _new_user()
    try:
        db = session()
        try:
            db.execute(update(User).where(User.user_id == user["user_id"]).values(
                locked_until=datetime.now(timezone.utc) - timedelta(minutes=1)))
            db.commit()
        finally:
            db.close()
        logged_in, status = authenticate(user["email"], "Strong-Test-Password-2026!")
        assert status == "OK"
        assert logged_in["user_id"] == user["user_id"]
    finally:
        _cleanup(user["user_id"])


def test_mfa_recovery_code_expiration_and_single_use():
    from crownpath.auth import generate_mfa_recovery_codes, consume_mfa_recovery_code
    user = _new_user()
    try:
        code = generate_mfa_recovery_codes(user["user_id"], count=1)[0]
        assert consume_mfa_recovery_code(user["user_id"], code)
        assert not consume_mfa_recovery_code(user["user_id"], code)
        expired = generate_mfa_recovery_codes(user["user_id"], count=1)[0]
        db = session()
        try:
            db.execute(update(AuthToken).where(AuthToken.user_id == user["user_id"],
                AuthToken.token_type == "MFA_RECOVERY").values(
                expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
            db.commit()
        finally:
            db.close()
        assert not consume_mfa_recovery_code(user["user_id"], expired)
    finally:
        _cleanup(user["user_id"])
