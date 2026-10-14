# CrownPath — Instructor Safety Review Authorization Gap Analysis

**2026-10-14 · Read-only source inspection of `crownpath/main.py` on `main` · No code changes**

## Verified source behavior

- `current_user` checks a session cookie, active user and role-access release flag.
- `require_permission(permission)` delegates to `has_permission` for general permission checks.
- `INSTRUCTOR` access is gated by `CROWNPATH_INSTRUCTOR_ACCESS_APPROVED`; this is not an instructor-to-learner assignment.
- Owner staff-management routes can review instructor role requests and change roles.
- Learner endpoints use `academy.view` plus learner-role restriction and identify progress by authenticated `user_id`.
- No instructor safety-checkoff review endpoint or assignment enforcement was identified in the inspected `main.py`. This is a **scoped finding**, not proof that no assignment data exists elsewhere in the repository.

## Critical design distinction

General `academy.view` or `academy.manage` permission must **not** automatically grant access to every learner's checkoff. The future service needs an explicit learner-to-instructor assignment with a server-side object authorization check before reading or changing any assessment.

## Proposed authorization predicate

`can_review(actor, assessment)` requires ALL:
1. Actor authenticated, active, and instructor access approved.
2. Actor holds a newly defined checkoff review capability.
3. Assessment belongs to an approved course/pathway assigned to that instructor.
4. Assignment is active and matches the assessment learner and course.
5. Actor is not the assessment learner and has no disqualifying conflict.
6. Assessment is in a valid state for the requested transition.

Owner oversight should have separate audited read/override permissions, not implicit silent approval.

## Implementation review tasks

- Identify and review the canonical `has_permission` policy and current instructor-related models.
- Design a durable assignment record, effective/revoked timestamps and who can manage it.
- Require server-side assignment check for list, detail, review and revoke operations.
- Add synthetic negative tests for cross-learner and cross-pathway access, revoked assignments, self-review, stale requests and direct object-ID guessing.
- Keep all checkoff records separate from `LearnerProgress` and `LearnerLessonStep`.
- Confirm no assessment outcome is exposed as a professional license, diagnosis, or automatic certificate.

## Release gate

The existing instructor role **alone is insufficient evidence of safe per-learner grading authorization**. Do not implement or activate checkoffs until authorization design, privacy/security review, and owner sign-off. No deployment, merges, environment changes or real-participant processing were performed.

Related: [Instructor review workflow](CrownPath_Scalp_Lab_Instructor_Review_Workflow_v0_1.md), [Safety checkoff contract](CrownPath_Scalp_Lab_Safety_Checkoff_Contract_v0_1.md).
