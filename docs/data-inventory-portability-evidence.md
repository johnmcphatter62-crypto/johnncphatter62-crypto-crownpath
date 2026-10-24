# CrownPath Data Inventory and Portability Evidence — source review

Review scope: source files on draft PR #46 branch. No production data or secrets accessed. This is **not** a complete repository-wide or infrastructure audit.

## Confirmed ORM tables (crownpath/models.py)
| Data group | Tables | Data sensitivity | Export / retention status |
| --- | --- | --- | --- |
| Identity and authentication | users, auth_tokens | High: email, password hashes, MFA secrets, session/recovery hashes | Not verified |
| Instructor approval | instructor_requests | Personal statements, approval decisions | Not verified |
| Learning history | learner_progress, learner_lesson_steps | Student learning records | Not verified |
| Resource permissions | resource_assignments | Access-control assignments | Not verified |
| Audit history | audit_events | Actions, user IDs, event reasons, timestamps | Not verified |
| Audio service configuration | audio_stations, audio_zones, audio_schedules, audio_devices, audio_zone_devices | Provider/device identifiers and operational data | Not verified |

## Source observations
- `crownpath/db_config.py` requires an explicit database URL in production; local development defaults to SQLite.
- `crownpath/database.py` creates SQLAlchemy tables and a `system_metadata` table; its legacy SQLite connector is explicitly restricted to SQLite.
- `crownpath/main.py` has Owner role-protected account and curriculum routes; no dedicated data export or backup endpoint was identified in this file during this review.
- The ORM model inventory does not establish whether additional curriculum/payment data is held in separate modules, other tables, external providers, or object storage.

## Release gaps to resolve
1. Inventory remaining modules, migrations, uploads/object storage, and third-party processors.
2. Define safe export format, ownership checks, authorization, filtering, and audit events; **never export password hashes, MFA secrets, session hashes, or recovery hashes** to routine user exports.
3. Confirm encryption, backup schedule, retention, restore exercises, and provider exit process from verified infrastructure evidence.
4. Verify payment account ownership and payout integrity separately from database tables.
5. Exercise restore and export only with synthetic data in isolated infrastructure before approval.

All listed unverified controls remain OPEN. Do not claim production data portability or independent custody based on this review alone.
