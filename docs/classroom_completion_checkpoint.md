# CrownPath classroom completion checkpoint (isolated branch)

This is a source-inspection checkpoint, **not** a launch approval.

## Already implemented in `crownpath/main.py`
- `POST /api/auth/register`: creates a learner account and issues a session cookie.
- `POST /api/auth/login`: password sign-in, with MFA challenge for MFA-enabled accounts.
- `GET /api/learner/dashboard`: lesson catalog, per-lesson and overall progress.
- `POST /api/learner/lessons/{lesson_id}/open`: loads content and records progress.
- `POST /api/learner/lessons/{lesson_id}/steps/{step_index}/complete`: records an individual completed step.
- `POST /api/learner/lessons/{lesson_id}/complete`: marks lesson steps complete.

## Explicit restrictions already present
- Registration remains closed unless BOTH `CROWNPATH_LEARNER_ACCESS_APPROVED` and `CROWNPATH_LEARNER_ENROLLMENT_APPROVED` are true.
- Learner login/access remains gated by `CROWNPATH_LEARNER_ACCESS_APPROVED`.
- Owner testing is separate from learner release. Do **not** change flags in production to test.

## Finish sequence
1. Verify owner dashboard controls and curriculum authoring screens against existing API endpoints.
2. Run disposable integration tests for registration, login, dashboard, opening lessons, completing steps, and persisted progress. Use synthetic users and a test database only.
3. Verify instructor approval and owner-only authorization boundaries.
4. Check the frontend for enrollment, classroom, progress, empty states, and mobile usability.
5. Review readiness for the purchased domain and hosting separately, without modifying DNS or deploying.
6. Only after owner review and required security gates, prepare a staged release decision.

## Deferred payment work
Experimental payment-MFA proof and logout adapters remain test-only. Do not wire them into live routes, enable real payments, or infer PostgreSQL race safety from SQLite tests.

**Change policy:** Keep this draft PR unmerged. No production DB, credentials, deployment, DNS changes, or live payment activation.
