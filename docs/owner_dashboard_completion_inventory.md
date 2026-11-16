# CrownPath owner dashboard — implementation inventory

Source-inspection record on the isolated development branch; not a claim of live UI readiness.

## Existing protected API capabilities
| Owner workflow | API endpoint | Required permission |
|---|---|---|
| View people | `GET /api/owner/users` | `staff.manage` |
| Change account role | `PATCH /api/owner/users/{user_id}/role` | `staff.manage` |
| Activate/deactivate account | `PATCH /api/owner/users/{user_id}/active` | `staff.manage` |
| Review instructor applications | `GET /api/owner/instructor-requests` | `staff.manage` |
| Approve/deny instructor application | `PATCH /api/owner/instructor-requests/{request_id}` | `staff.manage` |
| View curriculum | `GET /api/owner/curriculum` | `academy.manage` |
| Create program/course/unit/lesson/version | `POST /api/owner/curriculum/{programs,courses,units,lessons,lesson-versions}` | `academy.manage` |
| Review and approve lesson versions | `GET /api/owner/curriculum/lessons/{lesson_id}/versions`, `POST /api/owner/curriculum/lesson-versions/approve` | `academy.manage` |
| Completion dashboard | `GET /api/owner/curriculum/completion-dashboard` | `academy.manage` |
| Progress summary | `GET /api/owner/curriculum/progress-summary` | `academy.manage` |
| Structure audit and readiness | `GET /api/owner/curriculum/structure-audit`, `GET /api/owner/curriculum/readiness` | `academy.manage` |

## Immediate completion work
1. Inspect frontend screens for each existing owner API workflow; mark missing screens rather than rebuilding endpoints.
2. Exercise registration → login → learner dashboard → lesson steps → completion using synthetic accounts and disposable DB.
3. Confirm learner and instructor cannot invoke owner-only APIs.
4. Confirm owner approval and course-version publication workflow.
5. Keep enrollment release flags off until owner review and staging acceptance.

This document is an inventory, not a passing integration test or authorization to deploy.
