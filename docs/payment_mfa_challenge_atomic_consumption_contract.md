# Payment-specific MFA challenge atomic consumption contract

**Scope:** isolated design review after CI #861; no live MFA, payment route,
database migration, provider call, merge, or deployment. Production remains BLOCKED.

## Authoritative state and trust boundary

- The server issues an unpredictable challenge ID bound to authenticated Owner,
  signed-session identity, exact payment action and (where relevant) destination.
- Server verifies the actual MFA factor. Client claims such as `verified=true`
  are never accepted as evidence.
- Store challenge state and failed attempts in an authoritative database with a
  short expiry, consumed timestamp and revocation state.
- A valid challenge is not permission to change a provider destination without
  CSRF/origin checks and explicit Owner confirmation.

## Atomic consume operation

Inside one database transaction, check current active Owner, enrolled MFA,
unrevoked signed session and the challenge's verified, unconsumed, unexpired
state. Atomically claim exactly one challenge row with a conditional UPDATE
(or equivalent row lock) and require affected-row count = 1. A competing
consumer must receive a denial. Any failure rolls back the claim; do not
reuse a challenge across different action or destination parameters.

Before initiating an external provider mutation, persist an idempotency key
and an auditable operation record. Database transactions cannot atomically
commit with external provider APIs: retries must reconcile provider outcomes
using that idempotency key rather than replaying MFA authorization.

## Required synthetic acceptance matrix

1. One verified fresh challenge: first consume succeeds, replay fails.
2. Two simultaneous consumes: at most one succeeds; no duplicate operation.
3. Wrong Owner, session, action, or destination: deny without consuming.
4. Expired, unverified, revoked, rate-limited or already consumed: deny.
5. Concurrent logout, Owner deactivation or password change: define
   serialization and fail-closed ordering, test against PostgreSQL.
6. Inject transaction failure: no partially consumed challenge or audit record.
7. Simulate provider timeout/retry with fake provider: one idempotent mutation,
   accurate reconciliation and no sensitive data in audit logs.

## Limits

The current `eligible_payment_challenge` helper is a pure test-only policy;
it neither verifies MFA codes nor atomically consumes database records.
SQLite concurrency tests do not establish PostgreSQL behavior. Real route,
CSRF, provider and independent security review are still required.
