# Verified session context — implementation contract

This contract guides the next isolated test phase. It does not activate a route.

## Authoritative validation required

A server-side adapter for `payment_mfa_session_context.verified_session_context` must:

1. Read the authentication token from the HTTP-only session cookie, not a client JSON field.
2. Validate JWT signature, expiry, `purpose=session`, and string `sub` and `jti` claims.
3. Confirm the hash of `jti` matches an active, unrevoked `AuthToken` database row for the same user.
4. Re-fetch the user and confirm active status, approved role, and payment permission.
5. Return only the validated `user_id` and session `jti` to the internal payment authorization layer. Never log raw tokens or `jti`.

The current `decode_access_token` returns only user ID. Do not decode JWT claims separately without repeating authoritative validation, because doing so introduces a check/use race.

## Fail-closed lifecycle requirements

- On logout, password reset, account disablement or MFA reset, invalidate outstanding payment proofs tied to affected sessions.
- Handle simultaneous session revocation and proof consumption in a single reviewed transaction/lock ordering strategy.
- Bind each payment step-up proof to a single user, verified session, action purpose and expiry.
- Enforce fresh server-side MFA, CSRF/origin checks, rate limits and audit before provider access.

## Isolated acceptance tests to implement

- Valid signed and database-active session yields identity pair.
- Expired, tampered, wrong-purpose, database-revoked and cross-user session tokens yield no context.
- Logout/password reset invalidates session context and outstanding proofs.
- No fake-provider changes occur after any failed validation.

**Release gate remains BLOCKED** pending route integration, transaction design, and independent security review.
