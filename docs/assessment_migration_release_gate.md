# Chapter 100 — Practical Assessment Migration Release Gate

Status: **design and review only**. No production migration is authorized by this document.

## Current architecture
- `crownpath/models.py` defines `practical_assessments` and foreign keys to `users`.
- `migrations/env.py` uses SQLAlchemy metadata and the configured database URL.
- `crownpath/database.py` currently calls `Base.metadata.create_all()` at initialization; this is **not** a versioned schema migration.
- Assessment and audit records are staged in one SQLAlchemy session.

## Required pre-migration checks
1. Identify the live Alembic revision head(s) and deployed schema state; resolve any drift.
2. Verify the exact production database identity, backups, and a successful restore rehearsal.
3. Generate a versioned migration with a correct `down_revision`; review SQL for both PostgreSQL and supported local development databases.
4. Verify the migration creates `practical_assessments` with primary key, two user foreign keys, and indexes on learner, reviewer, and lesson.
5. Decide and implement database-level constraints for knowledge range (0–100), allowed decisions, and non-self-review; application validation alone is insufficient.
6. Check how legacy `create_all()` interacts with Alembic and prevent uncontrolled production schema creation.
7. Test clean installation, upgrade from the current schema, repeat upgrade, and rollback on an isolated staging clone.
8. Re-run authorization, assessment, audit, and PostgreSQL transaction tests.
9. Record change approval, maintenance/rollback steps, and post-migration verification.

## Release blocker
The preview endpoint is read-only. The review service does not yet verify that evidence references belong to the learner or that rubric identifiers and scoring inputs are trusted server-side. Do not expose the approval-writing service through an HTTP route until those controls are implemented and tested.

## Credentials
Internal CrownPath completion or assessment records are **not** North Carolina cosmetology/barber licenses.
