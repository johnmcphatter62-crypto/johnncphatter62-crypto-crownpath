# CrownPath AI-independent continuity and recovery gate

**Status: planning only — recovery NOT yet verified.**
No live data access, export, provider changes, production configuration, deployment, or merge.

## Ownership and independence requirements

CrownPath must remain usable for its essential classroom, curriculum, enrollment,
and Owner administration workflows without ChatGPT or another AI provider.
AI-powered features must fail gracefully, with clear non-AI alternatives.
A domain registration or repository alone is not a full recovery solution.

## Recovery inventory and owner verification

| Asset | Recovery requirement | Evidence still needed |
|---|---|---|
| Domain and DNS | Owner-controlled registrar, renewal, DNS records and recovery access | Verify GoDaddy ownership, renewal and DNS export |
| Application source | Owner-accessible Git repository plus encrypted offsite copy and pinned release | Verify repository access, reproducible build and independent copy |
| Curriculum/media | Versioned content exports with asset licensing and integrity hashes | Verify completeness, permissions and restore |
| Student and business data | Encrypted, access-controlled backups with retention and deletion policy | Verify schema, restore, privacy obligations and key custody |
| Hosting and secrets | Documented deployment procedure, secret rotation and replacement-host path | Verify Railway settings and secure recovery process without copying secrets into logs |
| AI integrations | Inventory provider dependencies and define graceful degradation | Test AI-disabled core workflows |
| Payment configuration | Do not copy cardholder secrets; use provider-approved backup and recovery | Security review and provider reconciliation |

## Recovery acceptance checks (non-production)

1. Export a sanitized test-only source and content inventory; record SHA-256 checksums.
2. Restore a disposable application and database from synthetic backups in an
   isolated environment, with no connection to production services.
3. Demonstrate core classroom, enrollment and Owner workflows with AI
   integrations disabled.
4. Test restore access controls, backup encryption and secret rotation using
   synthetic credentials; do not store recovery codes or private keys in Git.
5. Document restore duration, data-loss window, retention and accountable Owner
   approval before any real export.
6. Reconcile copyright, licensing, student privacy and deletion requirements
   before copying real records to any secondary location.

## Release and operational guardrails

- No claim of completed backup until a separate copy and successful restore
  have both been independently verified.
- No automatic exports of live student, financial or authentication records.
- No live DNS, Railway, payment, or GitHub main-branch changes without explicit
  Owner approval and reviewed rollback plan.
- Payment integration remains blocked by its separate security release gate.

**Next checkpoint:** Build a disposable, synthetic backup-and-restore smoke test.
