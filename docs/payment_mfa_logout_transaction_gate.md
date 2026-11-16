# Logout and payment MFA proof integration — release blocker

Source review: `crownpath/main.py` has `POST /api/auth/logout`, which calls `revoke_access_token(token)` and returns HTTP 503 if revocation fails. The payment MFA database proof prototype is not wired to this route.

## Integration contract (design only)
1. Decode and authenticate the session server-side, deriving owner ID and stable session ID from verified token claims; never accept either from client input.
2. Revoke the access token and unused payment proofs in **one transaction** on the same database connection, or make every proof-consumption operation independently check the current session revocation state atomically.
3. Reject proof consumption if the session was revoked or expired, even if proof TTL remains valid.
4. Never return successful logout while the server cannot confirm revocation. The existing logout path already handles a token-revocation exception with HTTP 503.
5. Include logout-versus-consume race tests, failed revocation tests, token rotation, multi-session isolation, and concurrent requests.
6. Require real shared database migration and operational audit logging before production use.

**Critical limitation:** `revoke_session_proofs` in `payment_mfa_db_proof.py` is a test-only primitive. It is not called by logout and does not independently validate the caller's session. Do not wire it to production without implementing the transaction/session contract above.

Production payments and step-up endpoints remain disabled.
