# CrownPath payment MFA route-level isolated test plan

**Status: design only — no live payment endpoint or deployment.** This plan defines tests to implement only after the server-side session and MFA interfaces are reviewed.

## Disposable test harness

- Use a temporary SQLite database or ephemeral PostgreSQL service, with fabricated OWNER, INSTRUCTOR, and learner identities.
- Exercise FastAPI request handling with `TestClient` and dependency overrides only in tests. Never use real credentials, MFA seeds, recovery codes, or provider accounts.
- Replace the payment provider with a fake that records attempted configuration changes; assert **zero** calls on all rejected requests.
- Derive identity and session solely from verified server-side test fixtures, never JSON fields supplied by the client.

## Acceptance matrix

| Scenario | Expected response or effect |
|---|---|
| Missing/forged/expired session cookie | 401; no proof issued or consumed; zero provider calls |
| Inactive or non-owner identity | 401/403; zero provider calls |
| MFA not enrolled, stale code, incorrect code, reused recovery code | Denied; zero provider calls |
| Login MFA only, no fresh payment step-up | Denied; zero provider calls |
| Missing/invalid CSRF token or origin | Denied; zero provider calls |
| Valid owner with fresh server-verified MFA and CSRF | One short-lived session-bound proof |
| Wrong session, wrong user, wrong purpose, expired proof | Denied; proof not usable for protected change |
| Replay or concurrent proof reuse | At most one authorized change |
| Logout/session rotation/password or MFA reset | Outstanding proofs invalidated; no change after revocation |
| Concurrent logout versus payment update | Deterministic fail-closed ordering; no update after logout commits |
| Provider rejection, timeout, retry | No silent success; auditable state and safe retry semantics |
| Attempted payment destination substitution | Denied unless separately verified and explicitly approved |

## Prerequisites before implementing route tests

1. Identify a server-verified session identifier and its revocation/rotation semantics in the current authentication storage.
2. Define a real server-side payment-specific step-up MFA verifier, with replay and rate limiting.
3. Choose CSRF/origin verification and transaction boundaries.
4. Specify provider-account verification, idempotency, and audit behavior.
5. Keep production integration blocked until implementation and independent review.

A passing isolated test suite **does not** mean these prerequisites exist. This document is a test specification, not a security sign-off.
