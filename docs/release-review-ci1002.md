# CrownPath review packet — CI #1002

Status: REVIEW REQUIRED / RELEASE BLOCKED. This packet is documentation, not independent approval.

## Pinned candidate and evidence

- Candidate source: `d3692bce356882846df587aa504e16f75b157944`, draft PR #58.
- Reconciled Owner-MFA work: draft PR #57; selected safeguards originate in draft PR #46.
- Verified CI: [run #1002](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/43966252156).
- Application: 1,162 passed, 17 skipped, 63 subtests passed.
- Owner access: 4 passed, 15 subtests passed; browser: 5 passed; migration: 1 passed.
- Dedicated disposable PostgreSQL: 11 passed; its XML check rejects skipped cases.
- The application XML check explicitly requires the enabled-setup and enrollment-rotation audit regression methods to execute and pass.
- Earlier CI #1000 did not collect the appended rotation-audit method. PR #58 corrected its placement; #1002 is the evidence for that particular assertion.
- No production database, payment account, payout destination, production backup or infrastructure ownership was verified.

## What this candidate establishes

| Safeguard | Covered synthetic evidence |
| --- | --- |
| Owner activation | Existing accounts are rejected without overwriting their credentials or promoting their role. |
| Owner authority | Privileged permission checks require both enabled MFA and an explicitly verified current session; expired/revoked sessions are denied. |
| MFA enrollment | Recovery records and enabled state commit together; stale setup cannot overwrite completed enrollment; enrollment rotation does not emit a logout event. |
| Logout audit | Session revocation and metadata-only logout event commit together; audit failure rolls back revocation and returns 503; retry creates one event. |
| PostgreSQL ordering | Covered logout-first/consume-first orders, double logout, session/proof lock timeouts, actual HTTP audit failures and unrelated-session isolation passed. |

These are scoped tests, not a comprehensive penetration test, operational stress test or production release certificate.

## Remaining blockers

| Gate | Current evidence | Closure requirement |
| --- | --- | --- |
| Independent security review | OPEN; this packet is prepared by the implementer | Separate reviewer examines the pinned source, integration boundaries and test logs, and records findings and disposition. |
| Fresh payment-specific MFA | Existing helpers accept a trusted verification record or boolean; they do not establish a complete live step-up route | Bind a server-verified challenge and one-use proof to the signed current session and exact action; never accept client assurance flags. |
| Shared proof persistence | Experimental helpers use a test-only proof table | Review an actual migration, keyed proof hashing, uniqueness, expiry, revocation and transaction boundaries before production use. |
| Provider and destination | Not verified | Authorized provider selection, business ownership and destination verification; provider-side idempotency, timeout and reconciliation contract. |
| Payment HTTP boundary | Not established by logout tests | Actual auth/MFA, CSRF/origin, rate limiting, redacted auditing and fake-provider negative tests on an isolated database. |
| Operations and release | OPEN | Recovery/rollback evidence, review signoff and explicit release authorization. |

Source references: `docs/payment_mfa_integration_gate.md`, `docs/payment_security_release_gate_ci858.md`, `crownpath/payment_access.py`, `crownpath/payment_mfa_stepup_test_policy.py`, and `crownpath/payment_mfa_db_proof.py`.

## Next isolated integration contract — proposed, not implemented

Use a fake provider and synthetic records only. Do not enable checkout, payouts or a production payment endpoint.

1. Derive actor and session IDs from a validated signed cookie and the authoritative session row. Recheck active Owner status and session MFA assurance.
2. Create a server-controlled challenge bound to the intended action and a canonical digest of its parameters. A 120-second maximum lifetime is proposed for review; clocks and expiry boundaries must be tested.
3. Verify a fresh authenticator/recovery code on the server. Consume the challenge once; enforce attempt limits. A login MFA claim alone does not satisfy this payment action.
4. Issue an opaque proof bound to actor, session, purpose, challenge and action digest. Store only its keyed hash and metadata in shared storage.
5. In one database transaction, recheck authorization, consume the proof conditionally, persist the authorized intent and write redacted audit evidence. Follow a consistent lock order with revocation.
6. Define fake-provider dispatch and retry semantics separately. Database locking cannot make an external provider call atomic with logout. Record the allowed ordering, cancellation limits, idempotency and reconciliation policy before any real provider integration.

## Acceptance matrix for that contract

| Scenario | Required outcome |
| --- | --- |
| Forged/revoked/expired session, inactive or non-Owner account | Deny; no proof or provider intent. |
| Client sends verified/recent-MFA/owner/session flags | Those assertions cannot grant authority. |
| Invalid/expired/replayed challenge or failed MFA | Deny without creating an actionable proof; enforce attempt policy. |
| Proof used by another session, user, purpose or changed payload | Deny; no provider mutation. |
| Two workers consume one proof | One authorized intent at most; stable provider idempotency key. |
| Logout or role change precedes authorization commit | Deny later authorization; preserve unrelated sessions. |
| Audit/intent persistence fails | Roll back proof consumption and intent; explicit failure response. |
| Provider accepts but response is lost | Retry/reconcile using the same idempotency key; no duplicate fulfillment. |
| Provider call is already in flight at revocation | Apply the explicitly reviewed ordering/cancellation contract; do not claim database-only tests cancel it. |

## Review decision record

- Independent reviewer: UNASSIGNED.
- Security findings disposition: OPEN.
- Provider and schema decisions: OPEN.
- Merge/deployment approval: NOT GRANTED.
- All review PRs remain unmerged. CI success does not authorize payment activation or deployment.
