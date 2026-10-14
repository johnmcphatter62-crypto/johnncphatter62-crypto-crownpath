# CrownPath — Camera Consent Contract v0.1 (Design Only)

**Status:** Proposal for issue #42, not implemented, deployed, or approved.

## Boundary and evidence

The reviewed `crownpath/main.py` defines Pydantic request models for registration, login, MFA, instructor requests, and curriculum management. It does not define a camera consent request model in the inspected definitions. `crownpath/models.py` likewise has no dedicated image-consent model in the reviewed definitions. Curriculum consent guidance is present, but this proposal must not be mistaken for working functionality.

## Proposed consent record (subject to privacy/legal review)

- `consent_id`: random opaque identifier.
- `subject_id`: authenticated synthetic subject ID in tests; never a name in object keys.
- `purpose`: controlled enum, initially `COSMETIC_EDUCATION_IMAGE`.
- `notice_version`: exact version of disclosure shown.
- `scope`: explicit permissions for capture, storage, instructor review, and any separately approved AI processing; no bundled marketing consent.
- `affirmative_choice`: true only after explicit action; no preselected acceptance.
- `granted_at`, `withdrawn_at`: server-generated UTC timestamps.
- `expires_at`: approved time limit; no indefinite default.
- `recorded_by`: authenticated actor; proxy consent requires separate legal review.
- `audit_reference`: non-image evidence of state transitions.

**Minimization:** No image bytes, full names, contact details, or secrets in the consent audit record. The consent ledger must not be publicly accessible.

## State machine

`NOT_GIVEN → ACTIVE → WITHDRAWN` or `ACTIVE → EXPIRED`. A new consent requires a new versioned record; withdrawn consent cannot be silently reactivated.

- **No valid ACTIVE consent:** reject image capture/upload/processing; allow the non-photo lesson alternative.
- **ACTIVE consent:** permit only individually approved uses, subject to separate authorization, upload validation and environment safeguards.
- **WITHDRAWN/EXPIRED:** deny new processing and retrieval, initiate deletion according to the approved retention and backup policy, and record the outcome without retaining image content.

## Proposed interface (not an API currently available)

- `POST /api/camera/consents`: submit a deliberate choice against a presented notice version; must authenticate, validate scope and enforce CSRF protections as applicable.
- `GET /api/camera/consents/me`: return only the requester's current consent status, never other users' data.
- `POST /api/camera/consents/{id}/withdraw`: idempotent withdrawal by authorized subject or approved delegate, initiating a deletion workflow.
- **No image upload endpoint in this design phase.**

## Reviewer decisions needed

1. Approved notice text, purpose, retention, age/guardian rules, and lawful consent basis.
2. Whether instructors may ever view images, and under what role/assignment and purpose.
3. Whether any AI processor is permitted (default **NO**).
4. Audit event content, backup erasure policy, accessibility and refusal experience.
5. Security review of authentication, authorization, replay/idempotency, CSRF, abuse throttling, and storage separation.

## Acceptance criteria

Use synthetic accounts only. Map to CAM-01, CAM-02, CAM-03, CAM-07, CAM-15 in [the acceptance matrix](CrownPath_Camera_Privacy_Acceptance_Test_Matrix.md). Record actual results and reviewer signatures; do not mark tests PASS merely because this contract exists.

**Gate:** NO-GO for real photos until issue #42, issue #41 and security/privacy review are satisfied and the owner explicitly approves.
