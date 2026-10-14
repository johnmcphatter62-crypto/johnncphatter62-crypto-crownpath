# CrownPath — Camera Privacy Acceptance Test Matrix

**Review-only test specification · 2026-10-13**

These tests describe **required future behavior**, not implemented or passing functionality. No real participant data or production resources may be used. Execute only in an authorized, isolated environment with synthetic images and accounts, after preview access controls are confirmed.

| ID | Scenario | Expected outcome | Evidence to capture |
|---|---|---|---|
| CAM-01 | Consent declined before camera use | No capture, upload, or image storage; non-photo learning remains available | UI outcome, audit event without photo |
| CAM-02 | Separate affirmative consent granted | Consent version, scope, actor, time and purpose recorded before upload | Redacted synthetic consent record |
| CAM-03 | Upload attempted without valid consent | Denied; no object or derivative created | API status and storage inventory |
| CAM-04 | Upload oversized, invalid format, or misleading file content | Denied with safe error; no retained object | Sanitized test log |
| CAM-05 | Learner A attempts to read Learner B image | Access denied even if object ID is known | Authorization test result |
| CAM-06 | Instructor without assigned access requests image | Access denied; access audit written | Role matrix and audit record |
| CAM-07 | Consent withdrawn | New capture, retrieval, and processing denied; deletion workflow starts | Synthetic revocation/deletion trail |
| CAM-08 | Delete request for an existing synthetic image | Original and derivatives removed within approved window; backup exception documented | Storage reconciliation evidence |
| CAM-09 | Retention period expires | Image no longer accessible; scheduled deletion recorded | Synthetic expiry test |
| CAM-10 | Preview environment attempts production image access | Blocked; credentials and storage namespaces isolated | Configuration attestation, denied request |
| CAM-11 | External AI/image processor disabled or not consented | No third-party transmission | Network/process configuration evidence |
| CAM-12 | Photo or consent error occurs | No secret, image payload, or sensitive metadata in logs or error response | Redacted log sample |
| CAM-13 | Public/unauthenticated visitor requests image URL | Access denied; no public asset URL or long-lived share link | Anonymous request result |
| CAM-14 | Camera lesson completed without a photograph | Learner can complete manual observation alternative | Synthetic learner progression |
| CAM-15 | Consent disclosure accessibility review | Clear purpose, recipients, retention, withdrawal, and accessible refusal path | Reviewer sign-off |

## Required evidence fields

For each test record: **test ID; code commit; isolated environment ID; synthetic fixture ID; tester/reviewer; execution date; expected outcome; actual outcome; PASS/FAIL/BLOCKED; sanitized evidence link; defect/issue ID; reviewer signature**.

A test marked **BLOCKED** is not a PASS. Automated CI passing on documentation changes is not evidence that camera privacy tests passed.

## Release gates

- Security reviewer: ___ / date ___
- Privacy reviewer: ___ / date ___
- Accessibility reviewer: ___ / date ___
- Owner final GO/NO-GO: ___ / date ___

**Default decision: NO-GO for real participant photos**, pending implementation, evidence, and owner approval. Do not enable enrollment, use real photos, alter deployments, or merge code based on this matrix alone.

Reference: [architecture baseline](CrownPath_Camera_Data_Flow_Architecture_Baseline.md) and [issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41).
