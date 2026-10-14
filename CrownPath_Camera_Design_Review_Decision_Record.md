# CrownPath — Camera Design Review Decision Record

**2026-10-13 · Review handoff · Status: PENDING**

This record gathers the camera safety design decisions in one place. It does **not** represent reviewer approval, working photo APIs, or passing privacy acceptance tests.

## Review documents

1. [Camera data-flow architecture baseline](CrownPath_Camera_Data_Flow_Architecture_Baseline.md)
2. [Consent contract v0.1](CrownPath_Camera_Consent_Contract_v0_1.md) — issue #42
3. [Storage and access threat model v0.1](CrownPath_Camera_Storage_Threat_Model_v0_1.md) — issue #43
4. [Image retention and deletion contract v0.1](CrownPath_Camera_Image_Retention_Deletion_Contract_v0_1.md) — issue #44
5. [Privacy acceptance test matrix](CrownPath_Camera_Privacy_Acceptance_Test_Matrix.md) — CAM-01 to CAM-15
6. [Scalp photo implementation gap review](CrownPath_Scalp_Photo_Consent_Gap_Review.md)

## Decision register — all currently OPEN

| ID | Required decision | Responsible reviewer | Decision / evidence |
|---|---|---|---|
| D01 | Whether photos are needed for the initial pilot at all | Owner + curriculum | OPEN |
| D02 | Approved consent notice, scope, guardian rules, withdrawal wording | Privacy/legal | OPEN |
| D03 | Approved storage provider, isolation, encryption and key handling | Security | OPEN |
| D04 | Learner/instructor/owner access matrix | Security + privacy | OPEN |
| D05 | Whether third-party AI image processing is permitted (default NO) | Owner + privacy | OPEN |
| D06 | Normal image retention, deletion target, backup expiry, legal hold | Privacy/legal + security | OPEN |
| D07 | Accessible non-photo alternative and refusal experience | Accessibility + curriculum | OPEN |
| D08 | Preview protection and synthetic-only test environment verified | Security/operations | OPEN |
| D09 | Synthetic CAM-01–15 evidence reviewed, failures resolved | QA + security/privacy | NOT EXECUTED |
| D10 | Owner authorizes implementation and separately authorizes any real-photo pilot | Owner | NOT AUTHORIZED |

## Reviewer sign-off

- Security reviewer / date / decision / evidence: **PENDING**
- Privacy reviewer / date / decision / evidence: **PENDING**
- Accessibility reviewer / date / decision / evidence: **PENDING**
- Owner / date / explicit GO or NO-GO / scope: **PENDING**

No implied approval from CI, a READY preview build, a document commit, or silence. A decision must identify reviewer, date, scope, and evidence.

## Safe near-term route

Continue the existing non-photo/manual scalp observation exercise using mannequins or synthetic materials while design decisions remain open. Do not invite real participants, enable learner enrollment, collect real images, merge, or deploy based on this record. Track overall approval in [issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41).
