# CrownPath recovery audit access release gate

Status: **BLOCKED for production**. This is a review checkpoint only.

## Evidence verified in development

- CI #894: disposable SQLite recovery approval transaction rollback.
- CI #895: synthetic recovery outcome audit records.
- CI #896: synthetic hash-chain audit modification and truncation detection.
- CI #897: synthetic secret-field exclusion policy.
- CI #898: synthetic Owner-only audit read policy.
- CI #899: actual FastAPI recovery-plan HTTP endpoint requires an authenticated session with `security.manage`; anonymous and learner requests are denied and logout revokes access.

These are independent tests, not proof of an integrated recovery audit workflow.

## Required before enabling an Owner recovery-audit endpoint

1. Define a dedicated `security.audit.read` permission or equivalent explicit authorization, and verify it is enforced by the real authentication/session dependency. Do not reuse a generic Owner flag without a security review.
2. Scope audit queries by school/tenant and enforce server-side authorization; never trust a school identifier supplied by the browser.
3. Apply strict pagination, bounded time filters, and an allowlist of response fields. Exclude credentials, MFA proofs, tokens, raw request bodies, and recovery secrets.
4. Define durable event writing for successful, denied, and failed recovery attempts. For external backup restoration, use an explicit durable state machine; do not assume a local SQLite transaction makes an external restore atomic.
5. Protect audit integrity with independently retained trusted digests or append-only/WORM storage and tested retention/restore procedures. A local hash chain alone is not tamper-proof.
6. Add real HTTP integration tests for Owner, instructor, learner, inactive Owner, revoked session, cross-tenant access, and missing permissions. Test audit read events and rate limiting.
7. Review retention, privacy, operational alerting, and incident-response procedures before release.

## Deployment gate

No live recovery-audit endpoint, production data access, merge, or deployment is authorized by this document. Require independent review and explicit Owner approval after the above controls and integrated tests are demonstrated.
