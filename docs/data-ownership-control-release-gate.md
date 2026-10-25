# CrownPath — Data Ownership and Control Release Gate

Status: DRAFT / evidence required. This document is a review checklist, **not** a claim that controls are already operational.

## Principles
- CrownPath's authorized business operator controls CrownPath business records and application administration, subject to student, employee, and customer rights and applicable law.
- Infrastructure vendors are service providers, not substitutes for CrownPath's authorization and data governance.
- No unapproved production access, database queries, secrets inspection, deployment, or merge is permitted during this review.
- Owner MFA is not to be bypassed or reset through unverified secondary Owner provisioning.

## Required evidence before launch

| Gate | Required verification | Status |
| --- | --- | --- |
| Data inventory | Identify student, instructor, course, payment, audit, and content records; classify sensitive data | OPEN |
| Database administration | Verify who holds production database and Railway organization administrative access, including offboarding | OPEN |
| Access controls | Review least-privilege roles, MFA, session revocation, and service credentials | PARTIAL: PR #46 CI checks; live verification outstanding |
| Backup and recovery | Verify encryption, retention, restore exercise on isolated data, and documented RPO/RTO | OPEN |
| Export and portability | Demonstrate authorized export in usable format and documented migration procedure | PARTIAL: learner self-export implementation and isolated PostgreSQL quota tests passed in CI #525; broader export, migration, and independent review outstanding |
| Privacy and retention | Define lawful processing, retention periods, user access/deletion workflows, and breach response | OPEN |
| Payment integrity | Verify payment provider account ownership, authorized payout destination, webhook validation, and audit trail | OPEN |
| Auditability | Verify immutable/append-only audit evidence for privileged access and sensitive data changes | OPEN |
| Vendor agreements | Review service contracts, subprocessors, exit terms, and domain/hosting account recovery | OPEN |
| Release safety | Complete isolated PostgreSQL MFA concurrency test and final independent security review | OPEN: learner-export PostgreSQL concurrency passed CI #525; separate MFA concurrency test and independent review not yet verified |

## Release decision
Keep PR #46 in draft and production unchanged until the gates have evidence and explicit authorized approval. A successful CI workflow is not proof of production data ownership or portability.

## Next safe work
1. Inspect repository-level data models and existing export/backup code without reading production data.
2. Write an evidence matrix for what is implemented, missing, and unverified.
3. Test with synthetic data only; do not use production credentials or databases.

## Learner export evidence update — 2026-10-25
- GitHub Actions CI #525: https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/40174566518
- Disposable localhost PostgreSQL 16 integration tests: four passed; includes ten concurrent requests, independent learner quotas, expired quota handling, and audit failure behavior.
- The learner-export quota verification is complete for these synthetic scenarios. Do not interpret this as proof of production deployment, comprehensive portability, cross-process stress testing, or MFA concurrency acceptance.
