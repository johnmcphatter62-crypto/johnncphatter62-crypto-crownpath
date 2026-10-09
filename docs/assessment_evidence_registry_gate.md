# CrownPath trusted assessment evidence registry — design gate

The Chapter 102 assessment service now rejects evidence unless it receives a
trusted server-side ownership mapping. This is a **fail-closed integration
boundary**, not a deployed evidence registry.

## Required trusted registry contract
- Store an opaque evidence ID, learner ID, lesson ID, evidence type, consent
  status (where applicable), storage-object reference, created timestamp,
  and revocation/deletion state.
- Issue references on the server after an authenticated upload or observation
  submission; never accept a client-supplied owner as authoritative.
- Resolve ownership and lesson association using a server-side database query
  inside the assessment transaction.
- Reject missing, revoked, cross-learner, cross-lesson, or duplicate references.
- Enforce object-storage access controls, retention/deletion policies, and
  appropriate consent checks for photographs or video.
- Never label camera observations as X-rays or medical diagnoses.

## Release blockers
The service currently receives a mapping from its caller; no verified registry
lookup or upload endpoint exists yet. Do not expose assessment-writing routes
until the server-side registry is implemented, tested, and wired to the service.
No production schema migration or deployment is authorized by this document.
