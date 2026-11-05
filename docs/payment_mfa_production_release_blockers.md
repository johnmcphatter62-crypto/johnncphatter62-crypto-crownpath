# Payment MFA proof integration: production release blockers

Status: **BLOCKED — experimental isolated code only.** No payment route or production schema integration is authorized by passing CI.

## What isolated tests currently demonstrate

- Only authorized, active, MFA-enrolled OWNER records satisfy the pure issuance and consumption guards when all required *server-derived* booleans are explicitly true.
- Proof records bind user, session, purpose, and expiry; consumption is a single conditional database update.
- SQLite and disposable PostgreSQL tests exercise replay, expiry, session mismatch, revocation, concurrency, and malformed inputs.
- The guards **do not** independently verify the claimed session, CSRF token, MFA result, or payment provider identity.

## Required before any live integration

1. **Authenticate the session server-side.** Resolve the user and an unguessable, stable session identifier from the signed and server-validated session; reject revoked, expired, rotated, and logged-out sessions. Never accept user/session identity from request JSON.
2. **Verify MFA server-side for the payment step-up.** Validate the fresh TOTP/recovery challenge with server-held verifier and anti-replay/lockout controls. Do not treat a login MFA flag, client boolean, or enrollment status as proof of a fresh step-up.
3. **Verify CSRF server-side** against the authenticated session and apply secure cookie attributes, origin policy, and request rate limits. Pass the trusted result into the pure guard only after validation.
4. **Issue proofs only after all checks pass**, in a transaction with audit records, and ensure the proof is bound to the exact current session, owner, and `payments.configure` purpose.
5. **Consume atomically in the same transaction as the protected authorization decision**, or ensure no provider-setting change can occur if the proof is rejected. Handle retries and failures without allowing duplicate configuration changes.
6. **Revoke outstanding proofs on logout, session rotation, password reset, MFA reset, or account disablement.** Confirm the order of session invalidation and revocation under concurrency.
7. **Protect payment destination changes** with provider-account ownership verification, allowlisted configuration changes, redacted audit trails, change notifications, and a recovery/rollback procedure.
8. **Add route-level integration tests** for missing/forged cookies, expired sessions, CSRF failure, stale/replayed MFA, recovery-code reuse, non-owner access, concurrent updates, logout races, and provider errors.
9. **Review the database migration and security design** separately before enabling any production route. Keep credentials and real provider calls out of CI.

Passing tests for the current helper functions is **not** evidence that these release blockers have been satisfied. The owner must explicitly authorize a separately reviewed production rollout.
