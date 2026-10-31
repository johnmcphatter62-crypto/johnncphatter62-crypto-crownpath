"""Experimental payment step-up freshness policy. No real MFA verification.

Caller must verify MFA independently on the server and supply a trusted
verification record. Not connected to routes, database or payment providers.
"""
from datetime import datetime, timedelta, timezone


def fresh_payment_stepup(record, *, user_id, session_id, action, now=None, max_age_seconds=120):
    if not isinstance(record, dict):
        return False
    if not all(isinstance(x, str) and x.strip() for x in (user_id, session_id, action)):
        return False
    if record.get("verified") is not True or record.get("consumed") is not False:
        return False
    if record.get("user_id") != user_id or record.get("session_id") != session_id:
        return False
    if record.get("action") != action:
        return False
    verified_at = record.get("verified_at")
    if not isinstance(verified_at, datetime) or verified_at.tzinfo is None:
        return False
    if not isinstance(max_age_seconds, int) or isinstance(max_age_seconds, bool) or not 0 < max_age_seconds <= 300:
        return False
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None:
        return False
    age = now - verified_at
    return timedelta(0) <= age <= timedelta(seconds=max_age_seconds)
