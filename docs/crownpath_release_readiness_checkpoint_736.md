# CrownPath release-readiness checkpoint — CI #736

Status: **BLOCKED — isolated development evidence only.**

## Verified evidence

- GitHub CI #736 completed successfully for application, browser-smoke, owner-access, and migration jobs on commit `b01d970dbb1d3bcb81bd0e4b6acbaa0de7264c14`.
- Isolated synthetic tests cover cross-origin Owner mutations, role and account deactivation boundaries, revoked sessions, logout-cookie replay, and expired server-side sessions.
- `crownpath/startup_guard.py` requires production database and secret configuration, HTTPS, demo-mode disablement, backup-restore verification, security-test verification, and explicit Owner launch approval.
- `crownpath/recovery.py` describes a recovery *procedure*, not evidence of a completed restoration.
- `docs/payment_mfa_production_release_blockers.md` explicitly blocks live payment integration; payment MFA helpers remain experimental and isolated.

## Outstanding release gates

1. **Backup restore evidence:** Restore a sanitized backup into a disposable environment, validate integrity and migration compatibility, record evidence and reviewer approval. Never restore over production.
2. **Production configuration evidence:** Verify HTTPS, secure cookie behavior, managed secret configuration, database connectivity, and disabled demo features without exposing secret values.
3. **Security assessment:** Review account recovery, MFA step-up, rate limiting, audit logging, authorization, and operational incident response. CI success is not a substitute for an independent security review.
4. **Payment integration:** Keep disabled pending server-side step-up MFA, CSRF/session binding, provider ownership verification, atomic updates, migrations, audit trail, and negative route-level tests.
5. **Release authorization:** Obtain explicit Owner approval only after independent review of all release gates.

## Change boundary

This checkpoint documents evidence and unresolved risks only. It does **not** authorize a merge, live schema change, payment activation, DNS change, or production deployment.
