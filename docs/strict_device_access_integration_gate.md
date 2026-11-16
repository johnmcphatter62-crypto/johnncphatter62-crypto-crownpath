# CrownPath strict device access — integration gate

**Status: BLOCKED for HTTP exposure, hardware discovery, production deployment and live payments.**

## Verified in the isolated development branch

- Database-backed school membership resolution and active Owner approval checks.
- Read-only filtering of synthetic Bluetooth/Wi-Fi device records by learner and school.
- Fail-closed behavior for missing approvals, revoked memberships, ambiguous schools, malformed records and database errors.
- CI checks and disposable SQLite tests. These are **not** live device or browser permission tests.

## Remaining blockers

1. **Principal provenance:** Wire only to the existing server-authenticated session dependency. Never accept a user ID, school ID or role from request parameters, JSON or headers as authorization.
2. **Single canonical resolver:** Replace the permissive membership resolver with the Owner-verified resolver, and remove or deprecate redundant implementations after regression tests. The stricter implementation is currently staged separately.
3. **Database schema:** Verify SQLAlchemy model alignment, migration compatibility, constraints and PostgreSQL behavior. The current school tables are introduced through Alembic, not the app's model metadata.
4. **Approval provenance:** Establish which authenticated Owner is authorized to approve a membership for each school, not just whether the approver has an active global OWNER role. Audit creation, changes and revocations.
5. **Device provenance:** Define trusted, persistent device records and an enrollment/approval workflow. Synthetic dicts are not trustworthy discovery results.
6. **Consent and browser security:** Require explicit camera/microphone consent and browser permission handling. Treat Bluetooth and Wi-Fi capabilities as platform-dependent; never claim real hardware support based on synthetic tests.
7. **Authorization regression:** Add real HTTP dependency tests, cross-tenant tests, role checks, revocation races and error-path tests. Verify that disabled feature flags keep all new routes unavailable.
8. **Privacy and release:** Specify retention, minimization, redaction, audit events, incident response, accessibility and Owner sign-off before any deployment.

## Next safe milestone

Build an **offline test-only authenticated endpoint harness** with a feature flag defaulting to OFF, and verify unauthorized requests cannot reach any device data. Do not merge, deploy, enable the feature flag in production, or access live devices without explicit approval.
