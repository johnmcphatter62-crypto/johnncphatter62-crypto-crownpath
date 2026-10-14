# CrownPath — Camera Data-Flow Architecture Baseline

**2026-10-13 · Draft for review · No implementation or production changes**

## Inspected evidence (default branch)

- `crownpath/main.py`: FastAPI route inventory includes learner authentication, progress, curriculum, owner management, and other services. No photo-upload, photo-consent, or photo-deletion endpoint was identified in this inspected module. It references scalp camera lessons in the learner catalog, not an image capture API.
- `crownpath/models.py`: inspected SQLAlchemy model definitions include users, instructor requests, learner progress, lesson steps, auth tokens, resource assignments, audit events, and audio entities. No dedicated image asset or image consent model was identified in the inspected definitions.
- `crownpath/database.py`: creates model tables via SQLAlchemy; includes a development/preview SQLite compatibility helper with an explicit production PostgreSQL restriction.
- `crownpath/advanced_lesson_content.py`: teaches camera consent, standardized observation, privacy, and stop/refer safeguards, but educational content is not a persisted consent record or storage implementation.
- `crownpath/experience_agent_lesson_content.py`: client experience curriculum; not an image-deletion handler.

**Scope limit:** Other source files, frontend assets, infrastructure configuration, integrations, migrations, and actual deployed services have not been exhaustively inspected. These observations do not prove the feature is absent across the full project.

## Intended photo lifecycle (not yet verified as implemented)

1. **Consent:** learner/model receives plain-language purpose, retention, recipients, withdrawal instructions; a separate affirmative choice is recorded. No consent => non-photo exercise.
2. **Capture:** camera access is explicitly user-initiated; no background capture; synthetic or mannequin data only in preflight.
3. **Upload:** authenticate and authorize request; validate file type, size, content and metadata; reject nonconsensual and oversized uploads; strip unnecessary metadata.
4. **Storage:** encrypted, private, environment-isolated object storage; random object keys; least-privilege access; never public static directories.
5. **Access:** subject-linked access control, signed short-lived retrieval, access audit, no instructor/learner cross-access.
6. **Processing:** no external AI/image processors unless explicitly approved and covered by separate disclosure and consent.
7. **Retention/deletion:** documented expiry, withdrawal workflow, object and derived-data deletion, backup limitations, audit without retaining sensitive images.
8. **Verification:** synthetic-data tests for denied consent, revoked consent, unauthorized access, expiry, deletion, and preview isolation.

## Architecture decision gate

**Do not implement or activate photo uploads until a security/privacy reviewer approves a storage design, consent model, data lifecycle, and test plan.** This draft is a technical planning baseline, not a commitment that a feature exists. Maintain a **NO-GO for real participant photographs** and use the existing manual non-image pilot exercise.

Track owner decision and reviewer evidence in [issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41).
