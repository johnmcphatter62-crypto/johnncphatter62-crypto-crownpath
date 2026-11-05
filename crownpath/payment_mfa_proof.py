"""One-time, purpose-bound, short-lived MFA confirmation for payment administration.

In-memory test primitive only: NOT suitable for production or multi-worker deployment.
A future implementation must use shared durable storage, atomic consume, and auditing.
"""
import secrets
import threading
import time

PURPOSE = "payments.configure"

class EphemeralPaymentMfaProofs:
    def __init__(self, *, clock=time.monotonic, ttl_seconds=120):
        self._clock = clock
        self._ttl = ttl_seconds
        self._tokens = {}
        self._lock = threading.Lock()

    def issue_after_verified_mfa(self, user_id: str, *, purpose: str = PURPOSE) -> str:
        if not user_id or purpose != PURPOSE:
            raise ValueError("Invalid MFA confirmation scope")
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._tokens[token] = (user_id, purpose, self._clock() + self._ttl)
        return token

    def consume(self, token: str, user_id: str, *, purpose: str = PURPOSE) -> bool:
        with self._lock:
            entry = self._tokens.pop(token, None)
        return bool(entry and entry[0] == user_id and entry[1] == purpose and self._clock() < entry[2])
