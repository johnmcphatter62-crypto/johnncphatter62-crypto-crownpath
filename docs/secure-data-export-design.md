# CrownPath — Secure Data Export Design (Review Only)

Status: **PROPOSED, NOT IMPLEMENTED**. No production data accessed or exported.

## Scope
Provide authorized, portable exports of CrownPath-controlled business and education records while honoring student and instructor privacy rights. Do not confuse a business-wide archive with a learner's own records request.

## Proposed export profiles
- **Learner self-service**: own profile fields and learning history only; no other users' records.
- **Owner business archive**: authorized business and education records, subject to applicable privacy and retention obligations; privileged MFA-verified session and auditable approval.
- **Compliance / subject request**: scoped records with verified identity, documented purpose, and redaction of unrelated individuals.

## Allowed-by-default fields for a learner export
- User: user_id, name, email, track, created_at.
- Learning progress: lesson_id, status, progress_percent, opened_at, completed_at, updated_at.
- Lesson steps: lesson_id, step_index, completed, completed_at, updated_at.

## Explicitly forbidden fields in routine exports
password_hash, mfa_secret, auth_tokens (including session and recovery hashes), reset tokens, activation codes, server environment variables, database connection strings, API keys, and private signing keys. Audit-event reasons and instructor statements may contain sensitive content and require separate policy review before export.

## Security controls required before implementing an endpoint
1. Authenticate every request and re-check active account and role permissions at execution time.
2. Require verified Owner MFA for any organization-wide export; never bypass MFA.
3. Filter learner exports by the authenticated user's server-side ID, never a client-supplied user ID.
4. Apply field allowlists (not serialize ORM objects wholesale); prevent relationship traversal.
5. Log requester, scope, purpose, export ID, outcome, timestamp, and record counts without logging sensitive record content.
6. Apply request throttling, export-size caps, time limits, and abuse monitoring.
7. Stream encrypted-at-rest temporary artifacts or use short-lived authenticated delivery; enforce expiration and deletion.
8. Document data subjects' rights, retention, lawful basis, and third-party disclosures.
9. Test horizontal and vertical authorization boundaries with synthetic users and verify excluded fields never appear.
10. Validate CSV injection protections if CSV is offered; prefer JSON with versioned schema and checksum manifest for machine portability.

## Proposed archive manifest
```json
{
  "format": "crownpath-export-v1",
  "scope": "learner-self",
  "exported_at": "ISO-8601 timestamp",
  "schema_version": 1,
  "files": [{"path": "learner.json", "sha256": "hex digest", "record_count": 1}]
}
```
The example is a format specification, not a generated export.

## Release gate
No production export endpoint should be enabled until privacy, security, and legal review is complete and tests demonstrate strict row/field isolation, authentication, auditing, and artifact cleanup.
