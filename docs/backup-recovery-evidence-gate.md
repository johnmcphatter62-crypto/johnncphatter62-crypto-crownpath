# CrownPath — Backup and Recovery Evidence Gate

Status: DRAFT / NOT VERIFIED IN PRODUCTION. This is a source-based review and a proposed synthetic restore exercise, not a backup or restore completion certificate.

## Confirmed source observations
- `crownpath/db_config.py` requires an explicit database URL when `CROWNPATH_ENV=production`; nonproduction defaults to a local SQLite demo database.
- `crownpath/database.py` defines SQLAlchemy initialization and a `system_metadata` table; its legacy `connect()` helper is SQLite-only and explicitly refuses PostgreSQL.
- These files do **not** demonstrate scheduled backups, encrypted backup storage, tested restoration, recovery objectives, or independent ownership of hosting and database accounts.
- The disposable PostgreSQL CI tests in run #529 validate MFA and learner-export behavior, **not** backup recovery.

## Minimum release evidence (all OPEN)
| Gate | Evidence required | Status |
| --- | --- | --- |
| Backup scope | Inventory database, uploaded assets, curriculum, configurations, and external payment records; document exclusions | OPEN |
| Schedule and retention | Written backup cadence, retention periods, and deletion controls | OPEN |
| Security | Encryption at rest and in transit, least-privilege backup credentials, restricted restore permissions, and key custody | OPEN |
| Restore drill | Restore synthetic backup into a fresh disposable database and verify data counts, referential integrity, and application reads | OPEN |
| RPO / RTO | Business-approved recovery point and recovery time targets with measured drill results | OPEN |
| Vendor exit | Verify access to exports and backup copies independent of one provider account | OPEN |
| Owner approval | Verified Owner MFA, documented operator approval, and independent reviewer signoff before production restore | OPEN |

## Safe synthetic PostgreSQL restore drill (proposed, not executed)
1. Use an isolated CI PostgreSQL service on localhost with a clearly disposable test database and synthetic identities only. Never connect to Railway or production.
2. Initialize the schema through the repository's normal test setup, then create a unique synthetic learner and progress/step records.
3. Export the disposable database using PostgreSQL's native dump utility, avoiding credentials in logs or command arguments.
4. Restore into a **second, newly created disposable** database within the same isolated CI job. Never overwrite the source database.
5. Compare expected synthetic record counts and selected field values, check relational references, and confirm the learner record can be queried through the restored SQLAlchemy session.
6. Verify that temporary dump files and both databases are destroyed when the CI job ends. Capture only non-sensitive test outcomes.
7. Fail the job if dump/restore commands fail, counts differ, referential checks fail, or the test is skipped.

## Boundaries
- A successful synthetic drill would verify only the tested schema and restore mechanics. It would **not** prove production backup scheduling, encryption, access control, retention, or recoverability.
- Do not download, inspect, or restore production backups during this review.
- Keep PR #46 in draft until all applicable release gates are evidenced and explicitly approved.

Related evidence: https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/40175149642
