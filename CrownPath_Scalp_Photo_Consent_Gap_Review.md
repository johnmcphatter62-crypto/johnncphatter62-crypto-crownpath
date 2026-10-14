# CrownPath — Scalp Photo Consent: Code-to-Policy Gap Review

**Scope:** Read-only inspection of `crownpath/main.py` and `crownpath/advanced_lesson_content.py` on `main`, 2026-10-13. This is **not** a complete repository-wide privacy/security audit.

## Verified in inspected files

- `advanced_lesson_content.py` includes consent and privacy instruction for both `cosmetology-scalp-camera-assessment` and `barber-scalp-camera-assessment`. It teaches standardized imaging, secure records, neutral visible observations, and referral rather than diagnosis.
- `main.py` maps both camera lessons into learner catalog entries.
- A keyword scan of the 608-line `main.py` found camera references in lesson catalog definitions, but **no explicit photo-upload, image-deletion, or photo-consent route** in that file.

## Not established by this review

- Whether other modules, services, or external storage implement photo upload and deletion.
- Whether a signed, separate image-consent record is persisted and linked to the correct participant.
- Whether consent withdrawal actually prevents further processing and triggers retention/deletion workflows.
- Whether any image or participant data can reach external AI services, logging, previews, or production resources.
- Whether a role-based access policy and image retention schedule are technically enforced.

**Important:** Curriculum instructions are not evidence of an implemented, verified consent workflow. Absence of a route in one file is not proof no implementation exists elsewhere.

## Pre-pilot reviewer actions

- [ ] Inventory all photo/camera endpoints, front-end upload controls, storage buckets, integrations, and third-party processors across the repository and deployment.
- [ ] For each data path, document purpose, lawful basis/consent, access roles, encryption, retention, deletion, audit trail, and environment isolation.
- [ ] Verify a separate affirmative photo-consent step before capture or upload; demonstrate refusal still permits a non-photo learning path.
- [ ] Test withdrawal/deletion using **synthetic** images and accounts; record expected vs actual outcomes and residual backups.
- [ ] Confirm previews and test services cannot receive real participant images before security approval.
- [ ] Require privacy reviewer sign-off and explicit owner GO/NO-GO before real photos or invitations.

## Temporary pilot constraint

Until implementation and deployment controls are verified, use mannequin observation or instructor-provided **synthetic/non-identifying examples**, and do not collect, upload, or store actual participant scalp photos in CrownPath. The manual non-image exercise described in `CrownPath_Private_Pilot_Readiness_Checklist.md` remains the fallback.

Track outstanding work in [issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41). No changes to production, enrollment, or deployment are authorized by this document.
