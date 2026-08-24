import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pyotp
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash

from crownpath.database import connect

password_hash = PasswordHash.recommended()

ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 30
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# Production must set this in a secret manager/environment.
SECRET_KEY = os.getenv("CROWNPATH_SECRET_KEY") or secrets.token_hex(32)

ALLOWED_SELF_REGISTER_ROLES = {
    "HOME_CARE",
    "BARBER",
    "COSMETOLOGY_PRO"
}

def now_utc():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.isoformat()

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
    token_hash = _hash_one_time_token(raw)
    token_id = f"CP-TOK-{uuid.uuid4().hex[:12].upper()}"
    created = now_utc()
    expires = created + timedelta(minutes=minutes)

    con = connect()
    try:
        con.execute(
            '''
            INSERT INTO auth_tokens
            (token_id, user_id, token_hash, token_type, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (token_id, user_id, token_hash, token_type, iso(expires), iso(created))
        )
        con.commit()
    finally:
        con.close()

    return raw

def consume_one_time_token(raw: str, token_type: str):
    token_hash = _hash_one_time_token(raw)
    con = connect()
    try:
        row = con.execute(
            '''
            SELECT * FROM auth_tokens
            WHERE token_hash = ?
              AND token_type = ?
              AND used_at IS NULL
            ''',
            (token_hash, token_type)
        ).fetchone()

        if not row:
            return None

        expires = datetime.fromisoformat(row["expires_at"])
        if expires < now_utc():
            return None

        con.execute(
            "UPDATE auth_tokens SET used_at = ? WHERE token_id = ?",
            (iso(now_utc()), row["token_id"])
        )
        con.commit()

        return row["user_id"]
    finally:
        con.close()

def create_user(name: str, email: str, password: str, role: str):
    role = role.upper()
    if role not in ALLOWED_SELF_REGISTER_ROLES:
        raise ValueError("This role cannot be self-assigned.")

    track = role
    user_id = f"CP-USR-{uuid.uuid4().hex[:12].upper()}"
    created_at = iso(now_utc())

    con = connect()
    try:
        con.execute(
            '''
            INSERT INTO users
            (user_id, name, email, password_hash, role, track, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                user_id,
                name.strip(),
                email.strip().lower(),
                hash_password(password),
                role,
                track,
                created_at,
            )
        )
        con.commit()
    finally:
        con.close()

    return get_user_by_id(user_id)

def get_user_by_email(email: str):
    con = connect()
    try:
        row = con.execute(
            "SELECT * FROM users WHERE email = ?",
            (email.strip().lower(),)
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()

def get_user_by_id(user_id: str):
    con = connect()
    try:
        row = con.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()

def _set_login_failure(user):
    attempts = int(user.get("failed_login_attempts") or 0) + 1
    locked_until = None

    if attempts >= MAX_FAILED_ATTEMPTS:
        locked_until = iso(now_utc() + timedelta(minutes=LOCKOUT_MINUTES))
        attempts = 0

    con = connect()
    try:
        con.execute(
            '''
            UPDATE users
            SET failed_login_attempts = ?, locked_until = ?
            WHERE user_id = ?
            ''',
            (attempts, locked_until, user["user_id"])
        )
        con.commit()
    finally:
        con.close()

def _clear_login_failures(user_id):
    con = connect()
    try:
        con.execute(
            '''
            UPDATE users
            SET failed_login_attempts = 0,
                locked_until = NULL,
                last_login_at = ?
            WHERE user_id = ?
            ''',
            (iso(now_utc()), user_id)
        )
        con.commit()
    finally:
        con.close()

def _is_locked(user):
    locked_until = user.get("locked_until")
    if not locked_until:
        return False

    until = datetime.fromisoformat(locked_until)
    return until > now_utc()

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
    con = connect()
    try:
        con.execute(
            "UPDATE users SET mfa_secret = ?, mfa_enabled = 0 WHERE user_id = ?",
            (secret, user_id)
        )
        con.commit()
    finally:
        con.close()
    return secret

def verify_mfa_code(user_id: str, code: str) -> bool:
    user = get_user_by_id(user_id)
    secret = user.get("mfa_secret") if user else None
    if not secret:
        return False
    return pyotp.TOTP(secret).verify(code, valid_window=1)

def enable_mfa(user_id: str, code: str) -> bool:
    if not verify_mfa_code(user_id, code):
        return False
    con = connect()
    try:
        con.execute(
            "UPDATE users SET mfa_enabled = 1 WHERE user_id = ?",
            (user_id,)
        )
        con.commit()
    finally:
        con.close()
    return True

def mark_email_verified(user_id: str):
    con = connect()
    try:
        con.execute(
            "UPDATE users SET email_verified = 1 WHERE user_id = ?",
            (user_id,)
        )
        con.commit()
    finally:
        con.close()

def update_password(user_id: str, new_password: str):
    con = connect()
    try:
        con.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hash_password(new_password), user_id)
        )
        con.commit()
    finally:
        con.close()

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
