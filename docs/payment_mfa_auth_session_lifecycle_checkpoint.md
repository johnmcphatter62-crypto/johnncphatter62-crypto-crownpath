# CrownPath authoritative session lifecycle checkpoint

**Read-only source inspection:** `crownpath/auth.py`, `crownpath/main.py`, and existing payment session contracts on development commit 09fa5507b9c1dcc1d82da300fed147ad822ae493. No live route, migration or deployment changed.

## Confirmed session model

1. `create_access_token(user_id)` generates a random `jti` and signs a JWT with `sub`, `purpose=session`, `iat`, and `exp`. It persists an `AuthToken` row of type `SESSION` with HMAC-SHA256 of `session:{jti}` and an expiry. The raw `jti` is not stored in that row.
2. `decode_access_token(token)` validates JWT signature and expiry, purpose, nonempty string `sub` and `jti`, and calls `_active_session` to confirm an unrevoked matching DB row. It returns only `user_id`, not `jti`.
3. `current_user(request)` takes the cookie, calls `decode_access_token`, reloads an active user, and checks role-release access. It does not yield a verified session context for payment MFA.
4. `revoke_access_token(token)` marks the matching SESSION row used and commits. `POST /api/auth/logout` calls it, but does not revoke experimental payment proofs.
5. `set_user_role` revokes active SESSION rows on role change or deactivation; `set_user_active` revokes active SESSION rows on deactivation. Neither function is wired to experimental payment proof storage.

## Existing design work (do not duplicate)

- `docs/payment_mfa_session_jti_boundary.md` already identifies the signed `jti` candidate.
- `docs/payment_mfa_verified_session_contract.md` already specifies trusted server-side validation.
- `crownpath/payment_mfa_session_context.py` and existing isolated tests provide experimental adapter coverage; verify their boundaries before designing another helper.

## Outstanding release blockers

- **P0 verified context:** expose `user_id` and `jti` only through a single authoritative server-side validation path; do not decode claims independently after `decode_access_token` and assume they remain valid.
- **P0 revocation atomicity:** design/verify transaction or locking strategy so logout, password/MFA reset, deactivation, and role changes invalidate outstanding payment proofs without a check/use race.
- **P0 payment step-up:** require new server-verified payment-specific MFA (login MFA alone is insufficient), CSRF/origin verification, and rate limiting.
- **P0 provider controls:** require explicit Owner approval, provider destination verification, idempotency, audit trail, and safe failure behavior.
- **P1 end-to-end evidence:** test real auth dependency boundaries with synthetic sessions and fake provider; preserve existing isolated coverage.

## Next safe checkpoint

Review `payment_mfa_session_context.py` against the actual `AuthToken` model and auth lifecycle. Document concrete interface mismatches and design a **test-only** integration contract. Do not wire a real payment route or promote the branch until independent review.

**Status: production payment integration BLOCKED.**
