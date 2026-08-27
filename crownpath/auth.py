import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pyotp
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from crownpath.database import session
from crownpath.models import AuthToken, User

password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

SECRET_KEY = os.getenv("CROWNPATH_SECRET_KEY") or secrets.token_hex(32)

ALLOWED_SELF_REGISTER_ROLES = {
    "HOME_CARE",
    "BARBER",
    "COSMETOLOGY_PRO",
}


def now_utc():
    return datetime.now(timezone.utc)


def _user_dict(user: User | None):
    if not user:
        return None
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "password_hash": user.password_hash,
        "role": user.role,
        "track": user.track,
        "active": user.active,
        "email_verified": user.email_verified,
        "mfa_enabled": user.mfa_enabled,
        "mfa_secret": user.mfa_secret,
        "failed_login_attempts": user.failed_login_attempts,
        "locked_until": user.locked_until,
        "last_login_at": user.last_login_at,
        "created_at": user.created_at,
    }


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(user_id: str) -> str:
    now = now_utc()
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except InvalidTokenError:
        return None


def _hash_one_time_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_one_time_token(user_id: str, token_type: str, minutes: int = 30) -> str:
    raw = secrets.token_urlsafe(32)
    token = AuthToken(
        token_id=f"CP-TOK-{uuid.uuid4().hex[:12].upper()}",
        user_id=user_id,
        token_hash=_hash_one_time_token(raw),
        token_type=token_type,
        expires_at=now_utc() + timedelta(minutes=minutes),
        created_at=now_utc(),
    )
    db = session()
    try:
        db.add(token)
        db.commit()
    finally:
        db.close()
    return raw


def consume_one_time_token(raw: str, token_type: str):
    token_hash = _hash_one_time_token(raw)
    db = session()
    try:
        token = db.scalar(
            select(AuthToken).where(
                AuthToken.token_hash == token_hash,
                AuthToken.token_type == token_type,
                AuthToken.used_at.is_(None),
            )
        )
        if not token or token.expires_at < now_utc():
            return None
        token.used_at = now_utc()
        user_id = token.user_id
        db.commit()
        return user_id
    finally:
        db.close()


def create_user(name: str, email: str, password: str, role: str):
    role = role.upper()
    if role not in ALLOWED_SELF_REGISTER_ROLES:
        raise ValueError("This role cannot be self-assigned.")

    user = User(
        user_id=f"CP-USR-{uuid.uuid4().hex[:12].upper()}",
        name=name.strip(),
        email=email.strip().lower(),
        password_hash=hash_password(password),
        role=role,
        track=role,
        active=True,
        email_verified=False,
        mfa_enabled=False,
        failed_login_attempts=0,
        created_at=now_utc(),
    )
    db = session()
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return _user_dict(user)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("An account with that email already exists.") from exc
    finally:
        db.close()


def owner_exists() -> bool:
    db = session()
    try:
        return db.scalar(select(User.user_id).where(User.role == "OWNER").limit(1)) is not None
    finally:
        db.close()


def create_owner(name: str, email: str, password: str, activation_code: str):
    configured_email = os.getenv("CROWNPATH_OWNER_EMAIL", "").strip().lower()
    configured_code = os.getenv("CROWNPATH_OWNER_ACTIVATION_CODE", "")
    supplied_email = email.strip().lower()

    if not configured_email or not configured_code:
        raise ValueError("Owner activation is not configured.")
    if supplied_email != configured_email:
        raise ValueError("Owner activation identity does not match.")
    if not hmac.compare_digest(activation_code, configured_code):
        raise ValueError("Invalid owner activation code.")
    if owner_exists():
        raise ValueError("Owner activation is already complete.")

    db = session()
    try:
        existing = db.scalar(select(User).where(User.email == supplied_email))
        if existing:
            existing.name = name.strip()
            existing.password_hash = hash_password(password)
            existing.role = "OWNER"
            existing.track = "OWNER"
            existing.active = True
            existing.email_verified = True
            existing.failed_login_attempts = 0
            existing.locked_until = None
            db.commit()
            db.refresh(existing)
            return _user_dict(existing)

        user = User(
            user_id=f"CP-USR-{uuid.uuid4().hex[:12].upper()}",
            name=name.strip(),
            email=supplied_email,
            password_hash=hash_password(password),
            role="OWNER",
            track="OWNER",
            active=True,
            email_verified=True,
            mfa_enabled=False,
            failed_login_attempts=0,
            created_at=now_utc(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return _user_dict(user)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Owner account could not be activated.") from exc
    finally:
        db.close()


def get_user_by_email(email: str):
    db = session()
    try:
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        return _user_dict(user)
    finally:
        db.close()


def get_user_by_id(user_id: str):
    db = session()
    try:
        user = db.get(User, user_id)
        return _user_dict(user)
    finally:
        db.close()


def _set_login_failure(user):
    db = session()
    try:
        row = db.get(User, user["user_id"])
        if not row:
            return
        attempts = int(row.failed_login_attempts or 0) + 1
        if attempts >= MAX_FAILED_ATTEMPTS:
            row.locked_until = now_utc() + timedelta(minutes=LOCKOUT_MINUTES)
            row.failed_login_attempts = 0
        else:
            row.failed_login_attempts = attempts
        db.commit()
    finally:
        db.close()


def _clear_login_failures(user_id):
    db = session()
    try:
        row = db.get(User, user_id)
        if row:
            row.failed_login_attempts = 0
            row.locked_until = None
            row.last_login_at = now_utc()
            db.commit()
    finally:
        db.close()


def _is_locked(user):
    locked_until = user.get("locked_until")
    return bool(locked_until and locked_until > now_utc())


def authenticate(email: str, password: str):
    user = get_user_by_email(email)
    if not user or not user["active"]:
        return None, "INVALID"
    if _is_locked(user):
        return None, "LOCKED"
    if not verify_password(password, user["password_hash"]):
        _set_login_failure(user)
        return None, "INVALID"
    _clear_login_failures(user["user_id"])
    return get_user_by_id(user["user_id"]), "OK"


def start_mfa_setup(user_id: str):
    secret = pyotp.random_base32()
    db = session()
    try:
        user = db.get(User, user_id)
        if not user:
            raise ValueError("User not found.")
        user.mfa_secret = secret
        user.mfa_enabled = False
        db.commit()
    finally:
        db.close()
    return secret


def verify_mfa_code(user_id: str, code: str) -> bool:
    user = get_user_by_id(user_id)
    secret = user.get("mfa_secret") if user else None
    return bool(secret and pyotp.TOTP(secret).verify(code, valid_window=1))


def enable_mfa(user_id: str, code: str) -> bool:
    if not verify_mfa_code(user_id, code):
        return False
    db = session()
    try:
        user = db.get(User, user_id)
        if not user:
            return False
        user.mfa_enabled = True
        db.commit()
        return True
    finally:
        db.close()


def mark_email_verified(user_id: str):
    db = session()
    try:
        user = db.get(User, user_id)
        if user:
            user.email_verified = True
            db.commit()
    finally:
        db.close()


def update_password(user_id: str, new_password: str):
    db = session()
    try:
        user = db.get(User, user_id)
        if user:
            user.password_hash = hash_password(new_password)
            db.commit()
    finally:
        db.close()


def public_user(user: dict):
    return {
        "user_id": user["user_id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "track": user["track"],
        "active": bool(user["active"]),
        "email_verified": bool(user["email_verified"]),
        "mfa_enabled": bool(user["mfa_enabled"]),
        "locked_until": user.get("locked_until"),
    }
