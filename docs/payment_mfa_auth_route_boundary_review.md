# CrownPath authentication-to-payment MFA boundary review

Scope: read-only inspection of `crownpath/main.py` on isolated branch. No routes changed.

## Observed current application behavior

- `current_user(request)` reads the `crownpath_session` cookie, decodes the access token, fetches an active user, and checks role release access. It returns a user record, **not** a server-verified session identifier or a fresh payment step-up assertion.
- `require_permission(permission)` depends on `current_user` and `has_permission`. It does not establish fresh MFA, CSRF, or session continuity by itself.
- `POST /api/auth/mfa/verify` validates an MFA login challenge and code, then issues a signed session cookie. **Login MFA is not a fresh payment-configuration step-up.**
- `POST /api/auth/logout` revokes the cookie access token; on revocation failure it returns 503. It does not revoke outstanding experimental payment MFA database proofs.

## Integration risks to resolve

1. The proof helper requires `session_id`, but the current authentication dependency does not supply one. Do not use client-provided session IDs or assume a cookie token string is an approved stable session identifier.
2. Session logout and payment-proof revocation are not transactionally coordinated. Review token revocation storage, transaction boundaries, and race handling before wiring any proof to routes.
3. No payment-specific step-up MFA challenge or server-verified CSRF evidence is passed to the proof-issuance guard.
4. No real payment-provider configuration endpoint is authorized for integration by this review.

## Next isolated work

Create a route-level test plan with fake sessions and fake provider calls for login/logout/session rotation, failed MFA, CSRF rejection, proof replay, concurrent logout, and authorization failures. Review auth storage and session invalidation before implementing a production route.

**Status: BLOCKED for production.** CI success for helper functions is not a release authorization.
