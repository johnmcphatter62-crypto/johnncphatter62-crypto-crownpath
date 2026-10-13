# CrownPath — Camera Storage and Access Threat Model v0.1

**Design-only review artifact · 2026-10-13 · Issue #43**

This document does not claim an implemented camera upload/storage system. Evidence inspected to date: `crownpath/main.py`, `crownpath/models.py`, `crownpath/database.py`, and camera curriculum. No operational image-storage control has been established from those files. No production or preview access test was conducted.

## Trust boundaries

1. **Browser/device:** camera permission and temporary local image data are untrusted.
2. **Authenticated API:** session identity, role, consent status, content validation, and rate limits must be enforced server-side.
3. **Private image storage:** application access is through narrowly scoped service identity; no public object listing.
4. **Image processing:** default disabled; external processors require separate review and affirmative scope.
5. **Preview vs production:** distinct credentials, storage namespaces, and access protection.
6. **Audit and backups:** minimal metadata only; backup retention/deletion limitations documented.

## Threats and proposed controls

| Threat | Control to design and verify | Related tests |
|---|---|---|
| User uploads without consent | Server checks active versioned consent before accepting bytes | CAM-01–03 |
| File disguises malicious content | Allowlist verified MIME/magic bytes; strict size limit; quarantine/reject; strip EXIF | CAM-04 |
| Guessable object ID / cross-learner access | Random keys, subject-linked policy checks for every retrieval, short-lived URLs | CAM-05, CAM-13 |
| Overbroad instructor access | Explicit assignment and purpose-limited permission, audited access | CAM-06 |
| Preview leaks production images | Separate storage accounts/keys, no production mounts, deny-by-default protection | CAM-10 |
| Unapproved third-party AI | No processor integration until approved and separately consented | CAM-11 |
| Images or secrets leak to logs | Never log image bodies, signed URLs, credentials or sensitive EXIF | CAM-12 |
| Revoked consent remains usable | Block retrieval/processing promptly and initiate verifiable deletion | CAM-07–09 |
| Static hosting exposes assets | Never store private images in frontend/static directories or public buckets | CAM-13 |
| Camera required for course completion | Maintain manual non-image learning path | CAM-14 |

## Engineering acceptance evidence

For each control, reviewer records: design decision, implementation reference, isolated synthetic test ID, expected/actual behavior, negative test, reviewer, date, and residual risk. Any unverified boundary is **BLOCKED**, not PASS.

## Required pre-implementation decisions

- Security/privacy approval of data classification and approved storage provider.
- Specific authorization model for learner, instructor, owner and support roles.
- Object lifecycle and backup erasure windows, consent withdrawal semantics.
- No real image collection or external AI until these gates and issue #41 owner GO are completed.

References: [architecture baseline](CrownPath_Camera_Data_Flow_Architecture_Baseline.md), [consent contract](CrownPath_Camera_Consent_Contract_v0_1.md), [acceptance matrix](CrownPath_Camera_Privacy_Acceptance_Test_Matrix.md).
