# CrownPath payment security release gate — CI #858 checkpoint

**Status: BLOCKED for production payment configuration.** This document reviews
isolated test evidence only. It is not a deployment, merge, or payment approval.

## Verified isolated evidence

- CI #858 passed all four jobs for commit `00c473f`.
- Test-only HMAC session-aware proof consumption checks matching unrevoked
  AuthToken, proof lifetime, single use, and active Owner with MFA enrolled.
- Synthetic tests cover revoked/expired/mismatched sessions, inactive Owners,
  role downgrade, disabled MFA, password-change rollback, and competing
  deactivation/role-change operations.
- SQLite serializes writers; passing races do not establish PostgreSQL
  transaction semantics or prevent a provider call already in flight.

## Required release blockers

| Priority | Gate | Required proof |
|---|---|---|
| P0 | Trusted session | Validate signed cookie/JWT, authoritative HMAC session row and Owner status; do not trust client assertions |
| P0 | Fresh step-up MFA | Server-verified, action-bound challenge, short TTL, rate limits, single-use and replay tests |
| P0 | CSRF and origin | Enforce origin and CSRF on cookie-authenticated payment mutations; test forged/missing values |
| P0 | Provider destination | Explicit Owner confirmation, verified account/destination, idempotency key and safe timeout/retry behavior |
| P0 | Revocation ordering | Prove no provider mutation can start after committed logout/password change/revocation; PostgreSQL concurrency evidence |
| P0 | Audit | Tamper-resistant event trail with actor, action, outcome and request correlation; no secrets or proof tokens |
| P1 | Integrated route tests | Real auth dependencies with disposable DB and fake provider, including denial and failure cases |
| P1 | Independent review | Security review, operational rollback and deployment approval |

## Next isolated acceptance work

1. Design and test a server-side payment-specific MFA challenge state machine,
   including expiration, failed attempts and one-time consumption.
2. Design CSRF/origin enforcement tests without exposing an HTTP payment route.
3. Add fake-provider idempotency and audit acceptance tests.
4. Review actual PostgreSQL transaction boundaries before any live integration.

**No production changes, migrations, live provider calls, merge or deployment.**
