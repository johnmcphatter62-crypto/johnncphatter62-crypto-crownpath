# Chapter 109 — Evidence storage schema migration release gate

Status: **development only; do not run against production**.

## Tables introduced on the development branch

- `practical_assessments`: instructor-reviewed learner assessment and decision
- `assessment_evidence_records`: learner/lesson evidence references, consent, revocation
- `evidence_storage_objects`: backend-owned storage metadata and completion state

## Safe migration preparation

1. Inspect existing Alembic files under `migrations/versions`, identify the actual revision head, and confirm the deployed `alembic_version` and schema. Never invent a `down_revision`.
2. Determine whether `Base.metadata.create_all()` has already created any of the tables outside Alembic. Plan for schema drift and pre-existing tables before running any revision.
3. Back up the target database and rehearse restoration on a disposable clone.
4. Prepare a versioned migration for the three tables, including foreign keys to `users`, indexes, and assessment check constraints. Verify downgrade dependencies in reverse order.
5. Add uniqueness constraints and policies for storage object reuse, evidence registration idempotency, consent provenance, and revocation lifecycle before enabling any write endpoint.
6. Verify fresh installation, upgrade from a realistic previous schema, repeated upgrade, rollback, and failed-upgrade recovery on staging PostgreSQL.
7. Ensure migration commands use an explicitly selected target database and cannot accidentally target production.
8. Keep instructor approval routes disabled until rubric trust, evidence type matching, secure object upload/verification, and authorization have been tested.

## CI regression note

Chapter 108 CI #323 identified a PostgreSQL test fixture ordering error:
`evidence_storage_objects.learner_id` referenced a `users` row that had
not yet been flushed. Chapter 109 flushes the learner before storage metadata.
The foreign-key constraint remains intact.

## Production status

No schema migration, object-storage deployment, or production approval endpoint
is authorized by this document. Internal completion records are not professional licenses.
