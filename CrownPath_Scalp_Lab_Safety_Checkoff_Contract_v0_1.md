# CrownPath — Scalp Lab Safety Checkoff Contract v0.1

**2026-10-14 · Design only · Not an implemented assessment service**

## Problem

In inspected `crownpath/main.py`, `POST /api/learner/lessons/{lesson_id}/complete` can mark all lesson steps completed without grading the proposed scalp lab safety-critical questions. Therefore **lesson completion is not proof of safety competence**.

## Separate status model (proposed)

- `NOT_ASSESSED`: no reviewed checkoff.
- `NEEDS_REMEDIATION`: one or more safety-critical items incorrect or missing.
- `PENDING_REVIEW`: learner submitted responses, awaiting authorized instructor review.
- `PASSED`: authorized reviewer verified all safety-critical answers and practical observation rubric.
- `REVOKED`: reviewer invalidated a prior pass with reason and audit event.

No status is inferred from `LearnerProgress.status` or progress percentage.

## Scope and data minimization

Applicable to `barber-hair-scalp` and `cosmetology-hair-scalp` only. Record opaque assessment ID, subject ID, lesson ID, rubric version, item pass/fail outcomes, reviewer ID, reviewed time, final status, and remediation reference. Do not store participant photos or medical histories. The first version may use a paper worksheet; online storage requires separate review.

## Proposed rubric

All three critical questions must be correct: (1) images cannot determine exact scalp pH; (2) pause and refer for an open/bleeding area; (3) do not diagnose disease from visible flaking alone. The practical rubric also requires neutral observation language and recognition of limits/referral. Any failed critical item => `NEEDS_REMEDIATION`; allow documented retraining and reattempt.

## Authorization and audit requirements

- Learner can see only their own result.
- Only an explicitly authorized instructor/reviewer assigned to the pathway can attest or revoke; owner oversight does not bypass audit.
- Reviewer's own result cannot be self-approved.
- Every pass, remediation, and revocation records actor, timestamp, rubric version and rationale.
- Repeat requests must not duplicate a pass or silently overwrite a revoked result.
- No certificate or public badge until separately approved.

## Proposed API shape — **not present in application**

- `GET /api/learner/safety-checkoffs/{lesson_id}` — own checkoff status.
- `POST /api/learner/safety-checkoffs/{lesson_id}/submit` — responses for instructor review.
- `POST /api/instructor/safety-checkoffs/{assessment_id}/review` — authorized attestation.
- `POST /api/instructor/safety-checkoffs/{assessment_id}/revoke` — authorized revocation.

These are interface suggestions only; no new routes or database tables were added.

## Isolated synthetic test plan

- SC-01: 100% lesson progress without checkoff returns `NOT_ASSESSED`.
- SC-02: Incorrect critical answer cannot pass.
- SC-03: All correct answers still require assigned reviewer attestation.
- SC-04: Learner cannot approve their own checkoff.
- SC-05: Instructor cannot approve outside assigned pathway.
- SC-06: Learner A cannot read Learner B result.
- SC-07: Retake preserves prior attempt history and reviewer evidence.
- SC-08: Revocation removes pass status without changing lesson completion.
- SC-09: No image/photo required for submission.
- SC-10: Duplicate review request is idempotent and audited.

All are **NOT EXECUTED**. Record actual results only in an authorized isolated environment.

## Approval gate

Curriculum, security/privacy, accessibility and owner review are required before implementation or any pilot claims. No production/staging changes, enrollment activation, merges, or deployment are authorized by this contract.

References: [non-photo lab](CrownPath_Non_Photo_Scalp_Observation_Classroom_Lab.md), [progress integration review](CrownPath_Non_Photo_Lab_Progress_Integration_Review.md), [owner review issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41).
