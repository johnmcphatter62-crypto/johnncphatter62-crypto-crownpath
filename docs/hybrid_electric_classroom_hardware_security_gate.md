# CrownPath — future hybrid electric classroom hardware security gate

**Status: DEFERRED / BLOCKED.** Planning checklist only. Nothing in this document
authorizes real hardware, Bluetooth/Wi-Fi discovery, camera capture, production
deployment, or payments. Current device visibility tests use synthetic records.

## Preconditions before even a supervised hardware pilot

- **Owner approval:** Document specific equipment, school, instructor, users,
  budget, pilot dates, and rollback plan. Obtain separate explicit approval.
- **Equipment safety:** Use appropriately certified equipment, manufacturer
  operating instructions, electrical inspections, and trained on-site supervision.
  Emergency stop and manual disconnection must work independently of CrownPath.
- **Identity and isolation:** Bind the learner to a server-authenticated account,
  one approved active school membership, and an authorized school Owner. No
  client-supplied school, role, or device ownership may grant access.
- **Registry and provenance:** Maintain a trusted school-owned device inventory,
  unique immutable identifiers, approval history, allowed transport, and
  revocation. Reject missing, duplicated, expired, or ambiguous entries.
- **Consent:** Ask separately before nearby-device discovery, pairing, camera,
  microphone, or saving images. Refusal must leave instruction usable without
  hardware. Consent must be revocable and clearly displayed.
- **Student privacy:** Saving material to a learner's own computer does not grant
  CrownPath permission to read it. Do not scan local files or upload content
  without a specific user-selected action and clear consent.
- **Hair/scalp imaging:** Educational visualization only; no X-ray claims,
  medical diagnosis, or inference of conditions from images. Define retention,
  deletion, instructor visibility, and access auditing before any capture.
- **Fail-safe behavior:** On logout, revocation, expired grants, network loss,
  school switch, or device mismatch, disconnect and deny new actions. Software
  must not bypass physical safety controls.
- **Security testing:** Test real authenticated routes, device firmware and
  browser permission behavior, cross-school access, session races, denial,
  timeouts, and recovery in a dedicated non-production environment.
- **Data governance:** Minimize telemetry; encrypt sensitive data in transit
  and at rest; document access logs, retention, incident response, and deletion.
- **Release gate:** Require reviewed pilot evidence, accessibility checks,
  instructor training, legal/privacy review where applicable, and a separate
  explicit Owner decision before merge or production deployment.

## Current boundaries

The staged policy only filters caller-supplied records. It cannot establish
physical equipment safety, validate live device ownership, or prove consent.
Passing CI does **not** satisfy this gate. The future 30-day curriculum may
include a simulated classroom exercise without connecting to actual hardware.

Related documents:
- `docs/future_hybrid_electric_smart_classroom.md`
- `docs/scoped_device_access_release_readiness.md`
