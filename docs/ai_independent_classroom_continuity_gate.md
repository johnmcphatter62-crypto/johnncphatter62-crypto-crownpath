# CrownPath AI-independent classroom continuity acceptance gate

**Status:** design checkpoint only. Synthetic backup/restore tests passed in
CI #869 and #870; this is NOT proof of live restoration or production readiness.

## Essential operations that must not require an AI provider

- Learner authentication and approved enrollment
- Viewing saved lessons, course outlines and authorized media
- Recording lesson completion and instructor review
- Owner management of courses, instructors and access permissions
- Audit, export and recovery of authorized records

## Required behavior when AI is unavailable

1. AI lesson assistant, avatar or scalp-analysis enhancements show a clear
   unavailable status without blocking the non-AI curriculum.
2. Classroom and Owner authorization checks continue to enforce the same
   permissions; AI outage must never bypass authentication.
3. User-generated or AI-generated content already lawfully stored remains
   readable according to normal access rules, without calling AI APIs.
4. New AI-dependent requests fail safely without charging students or
   losing saved coursework.
5. Logs record provider failure without recording secrets, student health
   details, private lesson submissions or raw credentials.
6. Re-enabling AI requires configuration and dependency checks, not a
   database restoration or a change of account ownership.

## Isolated acceptance tests to add

- Disable AI integration using synthetic configuration and exercise learner,
  instructor and Owner classroom flows.
- Verify authorized lesson reads and completion writes still succeed.
- Verify unauthorized access still fails closed.
- Verify AI-dependent features return an explicit unavailable result.
- Verify no network calls to an AI provider are attempted by core workflows.
- Restore fictional curriculum from an offline archive and reopen it.

## Release boundaries

Do not treat an isolated mock or test as evidence of a working live outage
fallback. Production acceptance requires actual route-level integration
tests, real backup recovery drills, documented ownership, and independent
review. No live data export, merge, or deployment is authorized here.
