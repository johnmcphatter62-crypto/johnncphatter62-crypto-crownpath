# CrownPath — Scalp Lab Instructor Review Workflow v0.1

**2026-10-14 · Review-only workflow specification · Not implemented**

## Objective

Provide a controlled instructor review of the non-photo scalp lab for `barber-hair-scalp` and `cosmetology-hair-scalp`. A learner's `LearnerProgress` percentage or `COMPLETED` status is **never** an assessment pass.

## Roles and boundaries

- **Learner:** submits synthetic exercise answers, sees own result and remediation instructions; cannot assign or change pass status.
- **Assigned instructor:** sees only authorized learner submissions in their pathway, evaluates rubric, attests pass or requests remediation.
- **Owner/auditor:** reviews decisions and audit history, without silent edits to prior assessments.
- **Unassigned instructor:** cannot read, grade, revoke, or enumerate learner records.

The assignment and authorization model must be confirmed against current code before any implementation.

## Instructor review sequence

1. Learner completes mannequin/synthetic-card worksheet with no personal photos or health information.
2. Learner submits three safety-critical responses and a neutral observation exercise (future feature; paper workflow remains possible).
3. System marks checkoff `PENDING_REVIEW`; ordinary lesson progress remains unchanged.
4. Assigned instructor compares answers to rubric version and confirms practical observation language and referral awareness.
5. **All critical answers correct + practical rubric met:** record `PASSED` with reviewer ID, timestamp, rubric version and evidence reference.
6. **Any critical answer incorrect or missing:** record `NEEDS_REMEDIATION` with item-level feedback, then permit a new attempt; do not overwrite the original attempt.
7. On discovered error or misconduct, authorized reviewer may `REVOKE` with reason; learner progress remains unchanged.
8. Learner sees outcome and next action, but never another learner's submission.

## Review record proposal

`assessment_id`, `attempt_id`, `learner_id`, `lesson_id`, `rubric_version`, `assigned_reviewer_id`, `submitted_at`, `reviewed_at`, `critical_item_results`, `practical_rubric_results`, `status`, `feedback_reference`, `revocation_reason` (when applicable). Keep minimal audit events without images or raw personal health details.

## Controls and unresolved design decisions

- Determine who creates and removes instructor assignments, and how conflicts of interest are handled.
- Specify what an instructor sees when a learner resubmits after remediation.
- Enforce role and object-level authorization server-side; do not trust user-supplied reviewer IDs.
- Prevent duplicate reviews and race conditions using idempotency/version checks.
- Provide an accessible text-only submission and manual paper review route.
- Define retention for student responses and audit records through privacy review.
- Do not issue certificates or imply professional licensure.

## Synthetic acceptance cases — NOT EXECUTED

| ID | Scenario | Expected |
|---|---|---|
| IR-01 | Learner submits correct critical answers | `PENDING_REVIEW`, not auto-pass |
| IR-02 | Assigned instructor approves valid attempt | `PASSED` with auditable reviewer |
| IR-03 | One critical answer incorrect | `NEEDS_REMEDIATION` |
| IR-04 | Learner retries after feedback | New attempt; earlier attempt preserved |
| IR-05 | Unassigned instructor attempts approval | Denied, no data disclosure |
| IR-06 | Learner attempts self-approval | Denied |
| IR-07 | Learner A requests Learner B result | Denied |
| IR-08 | Reviewer revokes prior pass | `REVOKED`; lesson progress unchanged |
| IR-09 | Duplicate approval request | Idempotent or explicit conflict; no duplicate audit pass |
| IR-10 | Paper-only exercise | Can be assessed without camera/photo upload |

## Gate

This is a review specification only. No new routes, tables, deployments, staging access, learner enrollment, or real-participant assessments were authorized or performed. Curriculum, privacy/security, accessibility, and owner sign-off remain pending. See [safety checkoff contract](CrownPath_Scalp_Lab_Safety_Checkoff_Contract_v0_1.md) and [owner review issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41).
