# CrownPath AI-outage route integration verification checklist

**Status:** test plan, not evidence that real routes have passed.
Current synthetic classroom continuity model: CI #872 green.

## Read-only route discovery before implementation

Identify actual route paths, auth/session middleware, database repositories,
and the AI provider integration boundary in the checked-out application.
Do not guess endpoints from the synthetic model. Record each confirmed route
and its source location in the test report.

## Required route-level test cases (disposable environment)

1. With AI provider access disabled, a signed-in learner can load an
   authorized published lesson and complete it; completion persists.
2. With AI disabled, an authorized instructor can review permitted lessons
   and an Owner can manage course metadata.
3. Unauthenticated and cross-account requests are rejected before any
   lesson data or private student information is returned.
4. AI-only features return a clear unavailable response without crashing
   unrelated pages or charging users.
5. Mock or block outbound network calls and assert essential classroom
   requests make no calls to AI providers.
6. A synthetic restored curriculum archive is readable through the
   application's actual lesson route, not only by a standalone file reader.
7. Verify session expiry, Owner deactivation, and role downgrade still
   prevent access during AI outage.
8. Capture test-only evidence: run ID, commit, route paths, passing assertions,
   and any untested assumptions.

## Exit criteria

- Test fixtures contain fictional student identities and content only.
- Tests execute against application routes and authentication middleware,
  not a self-contained model.
- No secrets, live student records, live payment requests, or real provider calls.
- Failures are fixed and rerun; CI is green for the exact commit.
- Independent review of privacy, permissions, and restoration remains required
  before a production release.

No deployment, merge, or production data export is authorized by this plan.
