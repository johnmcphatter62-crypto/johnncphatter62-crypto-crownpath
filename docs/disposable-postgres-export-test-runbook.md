# CrownPath disposable PostgreSQL export test — operator runbook

**Status: not executed.** Do not reuse production, restored production, or staging databases with real learner data.

## Preflight
1. Provision a **new empty PostgreSQL database** exclusively for this test, on an isolated local/container test instance or isolated testing service. Its database name must contain `disposable`, `crownpath_test`, or `test_crownpath`.
2. Independently verify host, project, database name, credentials, and network access are not shared with production. A name alone is insufficient evidence.
3. Do not print, commit, or paste the database connection URL into logs, issues, or PRs.
4. Install the project's development dependencies in a disposable runner. Set all of the following **locally in the runner**:
   - `CROWNPATH_ENV=staging`
   - `CROWNPATH_TEST_POSTGRES_URL` to the verified disposable PostgreSQL URL
   - `CROWNPATH_DATABASE_URL` to the **same exact URL**
   - `CROWNPATH_TEST_DB_DISPOSABLE=YES`
   - `CROWNPATH_LEARNER_ACCESS_APPROVED=true`
5. Run `python -m unittest tests.test_learner_export_postgres_concurrency -v`. Do not treat a skipped test as success.
6. Confirm ten parallel requests yield five HTTP 200 and five HTTP 429 responses, with five SUCCESS and five REJECTED audit entries. Record only sanitized test evidence.
7. Delete the isolated database after confirming test results; keep PR #46 draft until independent review.

## Outstanding
- CI success is not proof that the opt-in PostgreSQL test executed.
- Extend testing to separate worker processes, second learner isolation, rolling-hour expiry, and injected database failures.
- Never point this runner at production Railway PostgreSQL or any database containing real records.
