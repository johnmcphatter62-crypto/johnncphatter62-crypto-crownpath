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
| Export and portability | Demonstrate authorized export in usable format and documented migration procedure | OPEN |
| Privacy and retention | Define lawful processing, retention periods, user access/deletion workflows, and breach response | OPEN |
| Payment integrity | Verify payment provider account ownership, authorized payout destination, webhook validation, and audit trail | OPEN |
| Auditability | Verify immutable/append-only audit evidence for privileged access and sensitive data changes | OPEN |
| Vendor agreements | Review service contracts, subprocessors, exit terms, and domain/hosting account recovery | OPEN |
| Release safety | Complete isolated PostgreSQL MFA concurrency test and final independent security review | OPEN |

## Release decision
Keep PR #46 in draft and production unchanged until the gates have evidence and explicit authorized approval. A successful CI workflow is not proof of production data ownership or portability.

## Next safe work
1. Inspect repository-level data models and existing export/backup code without reading production data.
2. Write an evidence matrix for what is implemented, missing, and unverified.
3. Test with synthetic data only; do not use production credentials or databases.
