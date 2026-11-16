# Payment MFA: integration-readiness review after CI #620

**Verified:** CI #620 passed (394 application tests; owner-access and migration jobs passed). This reflects isolated helpers and test-only databases, **not** a live payment security system.

## Engineering decision

Stop expanding repetitive disposable session revocation cases for now. The highest-value next step is integration with the existing authentication model and a transactionally sound logout/proof-revocation design.

## Required implementation order

1. Review existing `AuthToken` schema and database session lifecycle in `crownpath/auth.py` and `crownpath/models.py`.
2. Add isolated tests using the **actual** `AuthToken` ORM model in a disposable database, not the parallel `payment_session_rows_test` schema.
3. Design and test coordinated logout and payment-proof revocation; ensure races and database errors fail closed.
4. Add real server-verified payment step-up MFA and CSRF checks in a non-production environment.
5. Test a fake provider behind an HTTP request boundary, including ownership and payment-destination integrity.
6. Obtain independent security review before any migration, merge or production activation.

## Outstanding blockers

The current signed-session adapter uses callbacks, and its SQLite store is a test-only model. It does not establish a production-authoritative user/session context. No real payment step-up endpoint, integrated proof revocation, or live provider safeguards have been verified.

**Release gate: BLOCKED.** Keep draft PR #47 unmerged; do not deploy, access secrets or production data, or activate payments.
