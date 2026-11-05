# CrownPath — school-scoped Owner approval gate

**Status: BLOCKED.** Passing CI does not authorize live device discovery or HTTP exposure.

## Gap

The staged `verified_owner_school_id` query checks whether an approver is active
and has role `OWNER`. It does **not** establish whether that Owner has authority
over the school whose learner membership is being approved. An active Owner from
school B could currently be recorded as approver for school A.

## Required data model and policy

- Add an explicit server-managed Owner-to-school authorization record, distinct
  from learner membership, with school ID, Owner user ID, active/revoked state,
  effective dates, and audit provenance.
- Enforce a unique, scoped authorization and referential integrity in the
  database. Define whether multiple Owners may administer one school.
- Approvals must verify that the approver is an active Owner **and** has an
  active authorization for that same school at approval time.
- Decide whether losing school authority retroactively invalidates prior
  learner approvals. Until that decision is reviewed, **fail closed** for
  device visibility if authority cannot be established.
- Never derive Owner-to-school authority from client-supplied role, school ID,
  query parameters, or a display name.
- Audit grant, revoke, and reassignment events with authenticated actor,
  timestamp, school scope, and reason. No secrets or raw device media in logs.

## Test acceptance criteria

1. Owner A authorized for school A may approve a school A learner.
2. Owner B authorized only for school B cannot approve school A.
3. Deactivated, revoked, expired, or demoted Owners cannot approve.
4. School authorization revocation removes device visibility on subsequent
   requests under the chosen fail-closed policy.
5. Cross-school and ambiguous grants fail closed; database errors deny access.
6. Migrations upgrade/downgrade in disposable PostgreSQL; no automatic grants.
7. Test-only HTTP requests use a server-authenticated principal, with feature
   flags OFF by default.

## Next implementation milestone

Stage an additive school Owner authorization migration and its disposable
database tests. Only after the schema and policy pass CI should the strict
resolver be updated. Do not merge or deploy without explicit Owner approval.
