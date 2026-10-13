# CrownPath — Camera Image Retention and Deletion Contract v0.1

**2026-10-13 · Design proposal for issue #44 · Not implemented**

## Evidence boundary

This is a proposed lifecycle for a future camera/image feature, not a claim that CrownPath currently stores or deletes participant photographs. Do not upload real images into preview or production environments. The policy durations below require privacy/legal and owner approval before implementation.

## Proposed data inventory

For every synthetic test image, maintain a reference to: subject ID, consent ID and notice version, opaque image ID, storage namespace, created time, approved expiry, derivative references, processor references (if any), deletion status and last audited transition. Never include image content or signed retrieval URLs in audit events.

## State transitions

`PENDING_UPLOAD → ACTIVE → DELETION_REQUESTED → DELETING → DELETED`

Alternate paths: `PENDING_UPLOAD → REJECTED`; `ACTIVE → EXPIRED → DELETION_REQUESTED`; `DELETING → DELETION_FAILED` (retry/escalate). No transition from `DELETED` back to `ACTIVE`.

### Triggers

- Consent withdrawn or expires.
- Subject requests deletion.
- Retention deadline reached.
- Owner/security reviewer orders a documented privacy purge.
- Image was collected in error or without valid consent (priority escalation).

### Denial before deletion completion

Once withdrawal or deletion is accepted, immediately deny new retrieval, transformation, external processing and new uploads under that consent, even while backend deletion is pending. The system must not imply physical erasure is complete until all tracked locations are reconciled.

## Proposed deletion workflow

1. Authenticate and authorize the request; record idempotency key and UTC timestamp.
2. Atomically mark image unavailable and queue deletion, preserving only minimum necessary audit metadata.
3. Revoke short-lived access grants and invalidate caches where feasible.
4. Delete primary private object and all registered thumbnails/derivatives.
5. Check processor copies and request erasure under any approved processor contract.
6. Reconcile expected object list against deletion confirmations; retry transient errors with bounded backoff and human escalation.
7. Record `DELETED` only after the approved deletion criteria are met; otherwise `DELETION_FAILED` or `PENDING_BACKUP_EXPIRY` with an honest user-facing status.
8. Explain immutable backup expiration windows and legal holds clearly; do not promise immediate irreversible deletion if backups remain.

## Retention policy questions — no invented defaults

Security/privacy reviewers and owner must decide: normal retention window; time to stop access after withdrawal; deletion service-level target; backup expiry; legal hold exception; audit record retention; data subject request handling; processor erasure obligations. **No specific duration is approved yet.** Avoid indefinite retention.

## Failure and abuse cases

- Repeated deletion request: idempotent, no duplicate work or disclosure.
- Unauthorized actor: deny without revealing whether an image exists.
- Deletion partially fails: inaccessible to users; retry and escalate; never report success prematurely.
- Restore from backup: reapply tombstones before restored data becomes accessible.
- Missing consent ledger: fail closed; quarantine/restrict image and escalate.
- Cross-environment request: cannot access or delete objects in another environment.

## Synthetic acceptance scenarios

- **CAM-07:** withdrawal blocks future access/processing and initiates deletion.
- **CAM-08:** primary and derived synthetic objects deleted; backup exception explicitly recorded.
- **CAM-09:** expiry initiates lifecycle purge and access denial.
- **CAM-05/06/13:** unauthorized deletion/read requests denied.
- **CAM-14:** non-photo learner path remains available.

For every scenario record expected result, actual result, code commit, isolated environment, synthetic fixture, tester, reviewer, evidence link, defect ID, and PASS/FAIL/BLOCKED.

## Release decision

Until approved implementation, isolated test evidence, privacy/security sign-off and owner GO (issue #41), **NO-GO for real participant images**. No deployment, merge, enrollment activation, or external AI processing is authorized by this contract.

See [acceptance matrix](CrownPath_Camera_Privacy_Acceptance_Test_Matrix.md), [consent contract](CrownPath_Camera_Consent_Contract_v0_1.md), and [storage threat model](CrownPath_Camera_Storage_Threat_Model_v0_1.md).
