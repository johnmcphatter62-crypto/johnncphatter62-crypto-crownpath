# CrownPath payment authorization integration gap review

**Scope:** Read-only review of the development branch at da08a5d94b20e42db7338d3f27499bb193eca860. No production changes, deployment, migration, payment provider calls, or merge. This is not a release approval.

## Observed application boundary

- `crownpath/main.py:current_user(request)` reads `crownpath_session`, decodes the access token, fetches an active user and checks role access; the dependency returns the user record. It does **not** return a separately verified session ID or fresh payment MFA assertion.
- `require_permission(permission)` checks role permission on that user, but does not itself verify a payment-specific MFA step-up or CSRF/origin token.
- `POST /api/auth/mfa/verify` verifies a login MFA challenge and issues the signed cookie. This is login MFA, not proof of fresh MFA for changing payment settings.
- `POST /api/auth/logout` calls `revoke_access_token(token)` and fails with HTTP 503 on revocation error. It does not call the experimental payment proof revocation helper.
- `crownpath/payment_mfa_db_proof.py` explicitly requires caller-side authenticated session/MFA checks and creates a **test-only** SQLite table; it is not wired to live routes.
- No CSRF implementation or payment configuration route was identified in the inspected `crownpath/main.py` text. This does not prove none exists elsewhere in the repository.

## Blocking gaps and required evidence

| Priority | Gap | Required before production payment configuration |
|---|---|---|
| P0 | Trusted session identity | Document a server-verified session identifier, expiration, rotation and revocation lifecycle; never accept a client-supplied session ID |
| P0 | Fresh payment-specific MFA | Server-side verified challenge bound to the Owner, session, action and short lifetime; rate limiting and replay resistance |
| P0 | Logout and revocation ordering | Prove outstanding proofs cannot authorize a provider change after session logout/revocation commits; define transaction and race semantics |
| P0 | CSRF and origin | Enforce and test CSRF/origin checks for cookie-authenticated payment state changes |
| P0 | Provider boundaries | Verified provider account/destination, explicit Owner confirmation, idempotency, rejection/timeout handling and audit trail |
| P1 | End-to-end route tests | Exercise real authentication dependencies with fake provider, disposable DB, forged/missing cookies, inactive/non-Owner, stale MFA, replay, concurrency, logout and failures |

## Safe next implementation order

1. Inspect authentication token storage and revocation implementation and write a server-session contract (read-only).
2. Design a payment-specific step-up MFA contract with synthetic tests and no live endpoint.
3. Design CSRF/origin, transaction ordering and audit/provider-idempotency contracts.
4. Only after independent review and explicit approval, consider implementation on an isolated branch; do not connect live payments or deploy by default.

**Gate: BLOCKED for production.** CI #835 and earlier green isolated tests establish only the behavior of the synthetic proof harness, not integrated payment security.
