# CrownPath — Backup Security, Retention and Recovery Policy (Draft)

Status: PROPOSED FOR OWNER AND SECURITY REVIEW. No production infrastructure or vendor configuration has been verified or changed.

## Data inventory and coverage
The recovery plan must cover the PostgreSQL application database, curriculum and uploaded assets (where stored), relevant application configuration, and the ability to reconstruct deployments from version-controlled source. External payment processors and third-party integrations need separate documented recovery and reconciliation procedures; never presume their data is included in a database dump.

Do not put live credentials, MFA secrets, signing keys, or raw environment variables into a general-purpose backup manifest or review package. Any authorized operational backup that necessarily includes sensitive authentication data must be treated as restricted, encrypted material with separate access controls.

## Proposed controls (not implemented)
- **Cadence:** consider automated daily full backups and more frequent recovery points where supported. Final schedule depends on agreed recovery objectives and vendor capability.
- **Retention:** propose daily backups for 30 days, weekly for 12 weeks, and monthly for 12 months **only as a starting proposal**. Legal holds, privacy obligations, deletion rights, and storage costs require review before adoption.
- **Encryption:** encrypted transport and encrypted storage, including copies outside the primary service; document key ownership, rotation, and recovery without recording key material in this repository.
- **Least privilege:** separate backup writer, restore operator, and reviewer roles. Require approved Owner access with MFA and logged, time-limited restore authorization.
- **Isolation:** maintain at least one independently controlled backup copy outside the primary failure domain, subject to approved vendor terms and access checks.
- **Integrity:** capture backup creation result, tool/database versions, backup size and checksum in a restricted evidence system; never publish raw backup files in CI artifacts.
- **Deletion:** ensure retention expiry and documented erasure procedures, including any legally required exceptions.
- **Testing:** conduct periodic isolated restores with synthetic data in CI; separately plan an authorized nonproduction restoration from a controlled backup once privacy/security reviews permit it.
- **Incident response:** document escalation contacts, recovery decision authority, communication steps, and post-restore reconciliation of learner progress and payments.

## Recovery targets — decision required
RPO (maximum acceptable data loss) and RTO (maximum acceptable service restoration time) are **not approved**. Owner and operational stakeholders must set them based on enrollment, course progress, payment impact, and actual infrastructure capabilities. Do not treat suggested backup intervals as committed RPO/RTO.

## Release gates still open
1. Verify production backup schedule, scope, encryption, retention, and restore permissions using authorized provider evidence.
2. Confirm asset storage, third-party integrations, and payment reconciliation coverage.
3. Demonstrate backup integrity and a representative, privacy-approved restoration without touching production.
4. Obtain written Owner approval, security review, and recovery-operator signoff.
5. Keep PR #46 draft and production deployment blocked until applicable gates are closed.

## Existing verified evidence
GitHub CI #539 passed one synthetic PostgreSQL dump-and-restore test, plus MFA and learner-export concurrency tests: https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/40176358041

This is evidence for **synthetic database restore mechanics only**; it does not establish production disaster-recovery readiness.
