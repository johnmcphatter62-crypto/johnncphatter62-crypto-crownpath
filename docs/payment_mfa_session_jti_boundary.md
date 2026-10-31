# Session identifier integration findings — isolated payment MFA review

Read-only inspection of `crownpath/auth.py` on the test branch.

## Verified implementation details

- `create_access_token` generates a random `session_id` and places it in the signed JWT `jti` claim; the database stores only `_hash_session_id(session_id)` as an `AuthToken` row.
- `decode_access_token` validates the signed JWT, its `purpose`, `sub` and `jti`, and checks for an active, unconsumed database session; it returns only the user ID.
- `revoke_access_token` marks the matching `AuthToken` row used and commits; it does not revoke any experimental payment proof.
- `update_password` revokes all active `SESSION` rows for the user.
- `verify_mfa_code` checks TOTP (with a time window) or consumes a recovery code, and uses account lockout handling. It is not a payment-specific step-up endpoint.

## Safe integration boundary

The signed `jti` is an existing session identifier candidate, but it **must not be accepted from request JSON or unverified JWT claims**. A future server-side dependency must validate signature, purpose, expiry, active database session, user status and role, then derive the session binding. Avoid exposing the raw `jti` in API responses or logs.

For logout and password change, payment-proof revocation must be coordinated with the authoritative session revocation. The current prototype proof table is separate, so atomicity and failure semantics require design before any route wiring.

## Next isolated implementation target

Design a verified-session-context helper that returns both user and session identity only after authoritative validation, and test rejection of forged, expired and revoked tokens using disposable database fixtures. Do not integrate payment configuration until MFA step-up, CSRF, provider ownership, and audit controls are implemented.

**Production release: BLOCKED.** No live route or production migration is authorized by this review.
