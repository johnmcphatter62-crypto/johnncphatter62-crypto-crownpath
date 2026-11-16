# CrownPath release-readiness checkpoint — CI #736

Status: **BLOCKED — isolated development evidence only.**

## Verified evidence

- GitHub CI #736 completed successfully for application, browser-smoke, owner-access, and migration jobs on commit `b01d970dbb1d3bcb81bd0e4b6acbaa0de7264c14`.
- Isolated synthetic tests cover cross-origin Owner mutations, role and account deactivation boundaries, revoked sessions, logout-cookie replay, and expired server-side sessions.
- `crownpath/startup_guard.py` requires production database and secret configuration, HTTPS, demo-mode disablement, backup-restore verification, security-test verification, and explicit Owner launch approval.
- `crownpath/recovery.py` describes a recovery *procedure*, not evidence of a completed restoration.
- `docs/payment_mfa_production_release_blockers.md` explicitly blocks live payment integration; payment MFA helpers remain experimental and isolated.

## Backup restoration checkpoint — CI #738

- CI #738 passed all four jobs on commit `b52ab90b8e3bc9f36ee33a5c6bc3b6713bc68eb3`.
- `tests/test_disposable_sqlite_backup_restore.py` creates a synthetic learner and progress record in a temporary SQLite database, copies it through SQLite's online backup API into a second temporary database, checks `PRAGMA integrity_check` and `PRAGMA foreign_key_check`, and verifies the restored records.
- **Scope limitation:** This proves a disposable SQLite backup/restore path under CI. It does not test a real CrownPath production backup, production PostgreSQL restore, disaster recovery timing, backup encryption, retention, or operational approval.
- **Release flag remains unverified:** Do not set `CROWNPATH_BACKUP_RESTORE_VERIFIED=true` on the basis of this isolated test.

## Production startup guard checkpoint — CI #740

- CI #740 completed successfully for application, browser-smoke, owner-access, and migration jobs at commit `8ffaf4402e6292ec285bfa98771f022c2cb2b0d5`.
- `tests/test_production_startup_guard_isolated.py` checks missing production database/secret settings, unsafe release flags, and expected behavior with fully configured *synthetic* values.
- **Scope limitation:** These are configuration-logic tests. They do not inspect or alter Railway, DNS, TLS termination, deployed secrets, backup systems, or a real production environment.
- **Release status unchanged:** No production launch approval or backup-verification flag is granted by CI #740.

## Outstanding release gates

1. **Backup restore evidence:** Perform an independently reviewed, non-production restoration of a representative production-format backup (sanitized as appropriate), validate integrity and migration compatibility, record recovery time and evidence, and obtain reviewer approval. Never restore over production.
2. **Production configuration evidence:** Verify HTTPS, secure cookie behavior, managed secret configuration, database connectivity, and disabled demo features without exposing secret values.
3. **Security assessment:** Review account recovery, MFA step-up, rate limiting, audit logging, authorization, and operational incident response. CI success is not a substitute for an independent security review.
4. **Payment integration:** Keep disabled pending server-side step-up MFA, CSRF/session binding, provider ownership verification, atomic updates, migrations, audit trail, and negative route-level tests.
5. **Release authorization:** Obtain explicit Owner approval only after independent review of all release gates.

## Change boundary

This checkpoint documents evidence and unresolved risks only. It does **not** authorize a merge, live schema change, payment activation, DNS change, or production deployment.
