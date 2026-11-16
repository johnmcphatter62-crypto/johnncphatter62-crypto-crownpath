"""Isolated payment-specific step-up challenge lifecycle policy.

This validates synthetic server-issued challenge state only. It does NOT
verify TOTP codes or provide a production MFA implementation.
"""
from datetime import datetime, timedelta, timezone


def eligible_payment_challenge(challenge, *, user_id, session_id, action,
                               now=None, max_age_seconds=120, max_failures=5):
    if not isinstance(challenge, dict):
        return False
    if not all(isinstance(v, str) and v.strip() for v in
               (user_id, session_id, action)):
        return False
    if challenge.get("user_id") != user_id:
        return False
    if challenge.get("session_id") != session_id or challenge.get("action") != action:
        return False
    if challenge.get("server_issued") is not True:
        return False
    if challenge.get("consumed") is not False:
        return False
    if challenge.get("verified") is not True:
        return False
    failures = challenge.get("failed_attempts")
    if type(failures) is not int or not 0 <= failures < max_failures:
        return False
    if type(max_failures) is not int or not 1 <= max_failures <= 10:
        return False
    if type(max_age_seconds) is not int or not 0 < max_age_seconds <= 300:
        return False
    issued = challenge.get("verified_at")
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(issued, datetime) or issued.tzinfo is None:
        return False
    if not isinstance(now, datetime) or now.tzinfo is None:
        return False
    age = now - issued
    return timedelta(0) <= age < timedelta(seconds=max_age_seconds)
