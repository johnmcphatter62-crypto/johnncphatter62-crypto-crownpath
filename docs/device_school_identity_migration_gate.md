# CrownPath school identity gate for device discovery

Status: **BLOCKED — design only, not deployed**.

## Verified repository findings (CI #921 baseline)

- `crownpath.models.User` has no `school_id` field.
- `crownpath.auth._user_dict` does not return a verified school identifier.
- `crownpath.main.current_user` validates the session, active state and role release flags, but does not establish school membership.
- `crownpath.device_visibility.visible_approved_devices` deliberately returns no devices when the principal has no verified `school_id`.
- `crownpath.database.init_db` calls SQLAlchemy `create_all`; this does **not** migrate existing tables. The repository has an Alembic configuration, so schema changes require an explicit, reviewed migration.

## Required implementation sequence

1. Define school and membership records with database-backed user-to-school relationships and active/revoked membership state. Do not accept a school ID supplied in a request as proof of membership.
2. Design an Alembic migration that creates new school and membership tables without dropping or rewriting existing user records. Check both empty SQLite and existing-database upgrade paths, and separately review PostgreSQL compatibility.
3. Make school assignment an Owner-authorized workflow. Verify the acting Owner's scope; never let learners self-assign or change schools by editing request parameters.
4. Resolve the school membership on the server for each authenticated request, and fail closed if membership is absent, ambiguous, inactive, or revoked.
5. Add device records with owner and school foreign keys, server-controlled approval/revocation fields, and database constraints. The current `AudioDevice` model is for playback and must not be repurposed as a learner's camera/Bluetooth/Wi-Fi authorization record.
6. Connect the actual `device_visibility` policy to a read-only authenticated endpoint only after database and authorization tests pass.
7. Add HTTP tests for unauthenticated access, forged school IDs, cross-school leakage, inactive membership, owner changes, revocation, and session expiration. Verify responses omit sensitive hardware identifiers.
8. Keep wireless discovery and camera/microphone permission requests behind their separate release gate; never trigger hardware access from a list endpoint.

## Release conditions

- All migration, authorization, HTTP, and browser tests green.
- Review of school ownership semantics, access revocation, and privacy retention.
- Explicit Owner approval before merge, production deployment, real hardware access, or live payments.

Until those conditions are met, **no live learner device discovery** is authorized.
