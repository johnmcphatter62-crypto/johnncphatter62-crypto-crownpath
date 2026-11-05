# CrownPath verified-session adapter versus actual ORM — isolated checkpoint

**Scope:** Read-only comparison on commit dec14bd87a03dbabf78af6ab3b93927931fe17a0. No live route, schema migration, payment operation, or deployment.

## Compared code

- `crownpath/payment_mfa_session_context.py:verified_session_context(token, decode_and_check=...)` is a fail-closed **test-only wrapper**. It accepts a callback and returns `(user_id, session_id)` only when that callback returns a dictionary containing nonempty strings. The wrapper **does not itself validate** a JWT, database session, active Owner, or permissions.
- `crownpath/auth.py:create_access_token` generates a random JWT `jti`, stores `HMAC(SECRET_KEY, 'session:' + jti)` in an `AuthToken` record, and signs the token.
- `crownpath/auth.py:decode_access_token` validates JWT purpose, expiry, typed `sub`/`jti`, and the active database record, but returns only user ID.
- `crownpath/models.py:AuthToken` has `user_id`, `token_hash`, `token_type`, `expires_at`, `used_at`; `User` has `role`, `active`, and `mfa_enabled`.
- `crownpath/main.py:current_user` verifies an active user and role release but returns the user record without session `jti`.

## Critical compatibility findings

1. **Hash format:** The production authentication store uses keyed HMAC with the `session:` prefix. Some isolated ORM tests use plain SHA-256 fixture hashes; those tests do **not** prove compatibility with `auth._hash_session_id`.
2. **Single validation boundary:** A future callback must validate signed JWT and DB row together, then return the verified `sub` and `jti` from the **same** trusted operation. Calling `decode_access_token` for the user and separately parsing claims risks stale-session/check-use races.
3. **Owner authorization:** The generic wrapper validates output shape only; production must independently enforce active Owner status, release permission, and fresh payment-specific MFA.
4. **Revocation:** `revoke_access_token` updates the `AuthToken` record, while experimental payment proofs live in a separate test table. Existing logout does not atomically invalidate payment proofs.
5. **No route activation:** A passing wrapper test cannot authorize payment configuration, CSRF bypass, or provider calls.

## Next isolated acceptance checks

- Add synthetic tests using the **real HMAC session-hash format** and the actual `AuthToken` ORM model, without touching the configured application DB.
- Verify forged/expired/revoked/wrong-owner JWTs and inactive users return no trusted context.
- Exercise concurrent session revocation and proof consumption only in disposable databases, and document remaining transactional gaps.

**Production payment integration: BLOCKED** until fresh step-up MFA, CSRF/origin, coordinated revocation, provider verification, and independent security review.
