# CrownPath Instructor Assignment Security — Design Gate

Status: DESIGN ONLY — no instructor write endpoints enabled, no production change.

## Existing boundary

- `INSTRUCTOR` has `academy.view` and `academy.manage_assigned` in the permission matrix.
- Owner curriculum creation/version/approval HTTP routes require `academy.manage`; instructors cannot use them.
- CI #759 verifies this restriction. It does **not** prove instructor-assignment editing exists.

## Required design before implementation

1. Introduce an explicit instructor-to-course assignment record, including instructor user ID, course ID, assignment status, assigned-by Owner ID, and timestamps. Add a database migration with a safe rollback plan.
2. Owner-only routes manage assignments. Never accept a client-supplied instructor identity as proof of authorization.
3. A separate instructor endpoint may create a **draft** lesson version only when the authenticated instructor has an active assignment to the lesson's parent course. Verify ownership in the same database transaction as the write.
4. No instructor endpoint may approve/publish lessons, change course ownership, modify assignments, or alter Owner security and payment settings.
5. Revocation must take effect on the next request; a removed assignment must block subsequent writes, including those from previously authenticated sessions.
6. Denied attempts must not modify curriculum records. Log allowed and denied changes without storing lesson contents, credentials, or tokens.
7. Add synthetic, disposable-SQLite tests for assigned-course allowed draft, unassigned-course denied draft, revoked assignment, disabled instructor, cross-course access, and Owner-only approval.
8. Keep the feature disabled by default until tests and a separate Owner acceptance review pass.

## Release guard

No production migration, DNS update, merge, real learner/instructor activation, or payment activation is authorized by this design document.
