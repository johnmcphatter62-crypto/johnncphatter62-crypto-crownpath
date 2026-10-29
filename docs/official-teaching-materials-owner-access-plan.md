# CrownPath official teaching materials — owner access security design

Status: DESIGN ONLY, isolated branch. No file upload, production storage, or publishing enabled.

## Policy
- Official CrownPath lesson materials must be submitted to CrownPath-managed storage.
- Instructors may retain local working copies, but a local-only file is **not** an official CrownPath record.
- Never scan or retrieve files from instructors' personal computers without explicit action and consent.
- Owner administrative access applies to CrownPath-managed business records, subject to privacy, retention, and applicable law.
- Contributor agreements must separately establish copyright ownership or licenses; uploading a file alone does not transfer copyright.

## Planned authorization
- Authenticated active instructors: submit a new **unapproved** file version only to courses for which they hold active assignments. Shared lessons require assignment to every containing course.
- Authenticated active Owner: list, review, export, approve, and revoke access to official files.
- Learners and unassigned or disabled instructors: cannot submit, edit, or view restricted files.
- Approval and publishing remain separate Owner-only operations.
- Every write and access-control change is audited with actor, timestamp, record ID, action, and result.

## Storage and validation requirements before implementation
- Store objects in private CrownPath-controlled storage; no public bucket or guessable download links.
- Validate MIME type from content, extension, size, malware scan status, and disallow executable or active-content uploads by default.
- Bind every object to immutable ID, uploader, course/lesson, content hash, version, approval state, and retention policy.
- Serve downloads only after authorization, with safe Content-Disposition and no-store headers.
- Encrypt in transit and at rest; isolate backup credentials and test restoration.
- Implement explicit retention, export, deletion/legal-hold, and instructor offboarding procedures.
- Document privacy controls for student records and minimize collection.

## Release gates
1. Design and contributor agreement review.
2. Isolated schema/storage adapter with synthetic files only.
3. Negative permission tests: unauthenticated, learner, revoked instructor, wrong course, shared lesson, forged ownership, cross-origin, and oversized/malicious content.
4. Owner export, audit, and backup/restore tests.
5. Explicit Owner approval and deployment review; never auto-merge or deploy.

This document is a plan, not evidence that any of these storage capabilities already exist.
