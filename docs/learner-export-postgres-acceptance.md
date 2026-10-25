# Learner export PostgreSQL concurrency test plan

Implementation commit: `0eb4652`.

The export route now obtains `SELECT ... FOR UPDATE` on the authenticated user's `users` row before reading the one-hour SUCCESS audit count and committing the SUCCESS/REJECTED event. PostgreSQL row locks should serialize competing requests for the **same account**, even across workers. SQLite does not enforce this row-lock guarantee.

## Disposable PostgreSQL acceptance test (executed in CI #525 on 2026-10-25)
1. Set up an isolated disposable PostgreSQL database with synthetic users and lesson records. Never use production credentials or data.
2. Configure staging application workers to point **only** to the disposable database.
3. Authenticate one synthetic learner, then synchronize ten parallel GET requests to `/api/learner/my-data-export`.
4. Expect exactly five HTTP 200 responses and five HTTP 429 responses, with five SUCCESS and five REJECTED audit events and no leaked records.
5. Repeat across separate worker processes and confirm a second learner has an independent quota.
6. Repeat with one-hour window boundary cases and simulated database failures.
7. Confirm all responses and audit events omit authentication secrets and other learners' records.

## Release gates
- CI #525 (commit `86c12f0`) executed four PostgreSQL integration tests successfully, including ten concurrent requests (five HTTP 200 and five HTTP 429), separate learner quotas, expired quota events, and failed audit transaction protection. Job logs show `Ran 4 tests` and `OK`. This verifies the covered synthetic scenarios, not production readiness. Multi-process worker verification, wider load/abuse testing, and independent security review remain open.
- The database lock protects one account's concurrent export quota, not global denial-of-service or request-volume controls. Consider infrastructure-level throttling separately.
- No merge or production deployment until review and approval.

## Evidence
- GitHub Actions run: https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/40174566518
- Dedicated job: `learner-export-postgres-concurrency` (PostgreSQL 16 service; localhost; disposable database; no production credentials)
- Four tests passed without skips; application, owner-access, and migration jobs also succeeded.
