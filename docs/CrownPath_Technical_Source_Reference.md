# CrownPath Technical Source Reference
## Architecture, APIs, Data, Security, Deployment & Integration Map

**Edition:** Technical / Owner & Engineering Reference

This document records the CrownPath technical architecture in printable form. It intentionally excludes passwords, private keys, API tokens, MFA secrets, database credentials, payment credentials, provider passwords, and other secrets.

---

# 1. System Purpose

CrownPath is a connected education and operations platform for Home Care, Barber, Cosmetology/Beauty & Wellness, digital learning, practical assessment, instructor workflows, client-support concepts, Avatar/Bot learning assistance, regulatory verification workflows, security, and Owner oversight.

The technical design keeps these functions connected through CrownPath Core rather than treating them as unrelated applications.

---

# 2. Primary Technology Stack

| Layer | CrownPath Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python + FastAPI |
| Validation | Pydantic |
| ORM | SQLAlchemy 2.x |
| Production database | PostgreSQL |
| Development/demo database | SQLite where appropriate |
| Source control | GitHub |
| CI | GitHub Actions |
| Production hosting | Railway |
| Web server | Uvicorn / ASGI deployment pattern |
| Authentication | Password hashing, JWT session tokens, MFA/recovery controls |
| Printable source | Markdown source documents with PDF/export workflow |

---

# 3. CrownPath Core Architecture

```text
                         CROWNPATH CORE
                              |
       -------------------------------------------------
       |          |          |          |              |
    Academy    Security   Operations   Content      Integrations
       |          |          |          |              |
   Learners     Auth       Owner      Lessons       Audio/Video
   Instructors  MFA        Audit      Printables    Email/Future
   Progress     Roles      Recovery   Avatar/Bot    Payments/Future
       |
 Home Care / Barber / Cosmetology / Beauty & Wellness
```

### Architectural Cycle

**CORE → SIGNAL → ACTION → FEEDBACK → PROTECTION → DIAGNOSTICS → CORRECTION**

Signals enter through authenticated user actions, learning progress, instructor decisions, monitoring, client workflows, or approved integrations. Actions are authorized server-side. Results generate feedback and records. Security and diagnostics then protect and evaluate the cycle.

---

# 4. Application Entry Point

The FastAPI application is defined in `crownpath/main.py`.

Core startup responsibilities include:
- application creation;
- security middleware;
- startup validation;
- database initialization;
- initial audio station/zone/device seeding;
- static frontend mounting;
- authentication endpoints;
- learner endpoints;
- instructor approval endpoints;
- Owner/admin endpoints;
- academy/content endpoints;
- health/readiness/recovery endpoints;
- audio/provider endpoints.

The application exposes `/api/health` as a basic application-health endpoint.

---

# 5. Frontend Architecture

CrownPath currently uses a lightweight browser frontend rather than requiring a heavy JavaScript framework.

### Responsibilities
- authentication forms;
- role-aware dashboard views;
- learner lesson navigation;
- lesson-step completion;
- Instructor Requests view;
- Owner controls;
- MFA setup/verification UX;
- digital-content presentation;
- Avatar Guide entry points;
- audio/status controls where exposed.

### Security Principle
Frontend visibility is not authorization. Protected actions must be validated by the FastAPI backend even when a button or panel is hidden from unauthorized users.

---

# 6. Database Architecture

CrownPath uses SQLAlchemy as the primary database abstraction.

### Engine
The database engine is created from the configured database URL with:
- SQLAlchemy future-style operation;
- connection pre-ping;
- SQLite thread compatibility when SQLite is selected;
- session factory with autoflush/autocommit disabled.

### Initialization
`Base.metadata.create_all()` creates mapped tables that do not yet exist. System metadata is also initialized.

### Production Rule
PostgreSQL is the production database architecture. Legacy SQLite-style direct connections are restricted to development/preview compatibility. Production code should use SQLAlchemy repositories/sessions/transactions rather than SQLite-specific query helpers.

---

# 7. Major Data Domains

## User / Identity
Representative information:
- user ID;
- name;
- email;
- password hash;
- role/track;
- active status;
- email verification state;
- failed-login/lockout state;
- MFA state.

## Authentication Tokens
Used for controlled token/session/recovery workflows. Server-side session records support revocation.

## Instructor Requests
Representative fields:
- request ID;
- requesting user;
- statement;
- status;
- reviewer;
- review note;
- reviewed timestamp;
- created timestamp.

## Learner Progress
Tracks lesson status, progress percentage, opening/update/completion timestamps.

## Learner Lesson Steps
Tracks individual completed lesson-step indexes so progress is based on actual step completion rather than a simple client-side completion button.

## Audio
Stations, zones, device mappings, schedules, and playback-state concepts.

---

# 8. Learner Pathway Architecture

Current learner roles:
- `HOME_CARE`
- `BARBER`
- `COSMETOLOGY_PRO`

Owner and Instructor roles are prevented from using learner-only progression as if they were learners.

### Home Care Catalog
- Client Safety & Home Care Foundations
- Sanitation & Infection Control
- Professional Communication
- Care Documentation
- Wellness Client Experience & Professional Boundaries
- Avatar & Bot Builder Foundations

### Barber Catalog
- Barbering Foundations
- Hair & Scalp Science
- Scalp Camera & AI-Assisted Cosmetic Assessment
- Cutting, Fading & Grooming
- Client Consultation & Shop Safety
- Beauty & Wellness Client Experience
- Fitness, Recovery & General Wellness Foundations
- Avatar & Bot Builder Foundations

### Cosmetology / Beauty & Wellness Catalog
- Cosmetology Foundations
- Hair & Scalp Science
- Scalp Camera & AI-Assisted Cosmetic Assessment
- Chemical Services & Product Safety
- Non-Surgical Hair Replacement & Scalp Application
- Professional Makeup Artistry
- Manicure & Pedicure Nail Care
- Wellness Massage Foundations & Scope Awareness
- Fitness, Recovery & General Wellness Foundations
- Integrated Beauty & Wellness Client Experience
- Avatar & Bot Builder Foundations

---

# 9. Curriculum Source Architecture

Curriculum is maintained as curated server-side Python data structures rather than requiring a database migration for every lesson-content revision.

Representative source modules include:
- `lesson_content.py`
- `advanced_lesson_content.py`
- beauty lesson content
- wellness lesson content
- cosmetology core lesson content
- barber core lesson content
- Home Care lesson content
- client-experience / agent lesson content

### Canonical vs Learner-Safe Content
The canonical curriculum may contain instructor-only fields such as:
- answer indexes;
- answer rationales;
- instructor notes;
- answer keys.

The learner-facing content path returns a sanitized deep copy with instructor-only keys removed.

### Critical Rule
Do not remove instructor answers from the canonical curriculum merely to protect learners. Protect them at the learner publication/API boundary so authorized Instructor Edition workflows can retain them.

---

# 10. Learner Progress Algorithm

For a lesson with `N` steps:

```text
completed_count = number of unique completed step indexes
progress_percent = round(completed_count / N * 100)
```

When all steps are complete:
- status becomes `COMPLETED`;
- progress becomes 100%;
- completion timestamp is recorded.

Individual step records are idempotent so repeating the same completion request should not artificially increase progress.

---

# 11. Authentication Architecture

### Passwords
Passwords are stored as secure hashes rather than plaintext.

### Session Token
Authenticated browser sessions use a JWT carried in an HTTP-only cookie.

Representative controls:
- HTTP-only cookie;
- secure-cookie behavior for configured HTTPS/production operation;
- SameSite protection;
- approximately 30-minute session lifetime;
- token purpose isolation;
- issued-at and expiration claims;
- server-side session identifier (`jti`) for revocation.

### Server-Side Session Record
A session JWT is paired with a protected server-side token record. Revocation marks the server-side session record used/revoked so possession of the old JWT alone is not sufficient after revocation.

### Legacy Compatibility
Older session tokens without the newer server-side session identifier were permitted only as a transition strategy so existing sessions could age out naturally.

---

# 12. Logout & Password-Change Revocation

### Logout
The intended architecture revokes the active server-side session and removes the browser cookie.

### Password Change / Reset
Changing the password revokes active server-side sessions so previously authenticated devices cannot continue indefinitely after credential recovery/change.

### Security Test Areas
- expired session rejection;
- MFA challenge cannot act as session;
- direct session revocation;
- password-change session revocation;
- MFA/recovery behavior;
- login throttling/lockout.

---

# 13. MFA Architecture

CrownPath supports time-based one-time password authentication.

### Flow
1. Authenticated user starts MFA setup.
2. Server creates a private MFA secret.
3. User adds the account to an authenticator application.
4. User submits a current authenticator code.
5. Server verifies the code and enables MFA.
6. Recovery codes are generated for emergency account recovery.

### Login with MFA
1. Password authentication succeeds.
2. Server returns a short-lived MFA challenge rather than a normal authenticated session.
3. User supplies authenticator or valid recovery code.
4. Successful verification creates the normal authenticated session.

### Security Boundary
MFA challenges use a different token purpose from authenticated sessions.

---

# 14. Recovery-Code Architecture

Recovery codes are one-time credentials.

Controls include:
- generated high-entropy/controlled-format codes;
- protected server-side hashes/HMAC rather than plaintext storage;
- user binding;
- atomic consumption;
- one-time use;
- recovery code excluded from ordinary public user output.

Never place real recovery codes in source control, printables, screenshots, or support messages.

---

# 15. Authorization Architecture

CrownPath combines role-based permission checks with object-level authorization where protected records require it.

### Roles
- Owner
- Instructor
- Home Care learner
- Barber learner
- Cosmetology learner

### Principles
- least privilege;
- server-side authority;
- protected resource ownership/assignment checks;
- Owner-only controls for sensitive administration;
- no Owner self-assignment through normal registration;
- no learner-to-Instructor promotion through ordinary role dropdowns;
- Instructor approval workflow required.

---

# 16. Instructor Approval API Domain

Representative operations:

```text
POST /api/instructor-requests
GET  /api/instructor-requests/me
GET  /api/instructor-requests          [Owner-controlled]
PATCH /api/instructor-requests/{id}     [Owner review]
```

Approval can activate the Instructor role/track. Review metadata is recorded.

---

# 17. Learner API Domain

Representative operations:

```text
GET  /api/learner/dashboard
POST /api/learner/lessons/{lesson_id}/open
POST /api/learner/lessons/{lesson_id}/steps/{step_index}/complete
```

A legacy/internal whole-lesson completion route may remain for compatibility, but the learner UI progression model is step-based.

### Pathway Enforcement
A learner can open only lesson IDs present in their role catalog. Cross-track lesson access is rejected.

---

# 18. Content Protection Layer

Learner content is sanitized recursively before delivery.

Restricted key categories include:
- `answer_index`
- `rationale`
- `instructor_notes`
- answer-key structures
- instructor-only correct-answer metadata

### Testing Requirement
For representative lessons across Home Care, Barber, and Cosmetology:
- questions/options remain available;
- restricted answers do not appear;
- steps remain intact;
- completion still reaches 100%.

---

# 19. Security Headers

CrownPath applies security middleware intended to provide protections such as:
- MIME sniffing prevention;
- framing restrictions;
- restrictive referrer policy;
- browser feature restrictions for camera/microphone/geolocation unless intentionally enabled;
- no-store behavior for sensitive responses where configured;
- HSTS when HTTPS is required.

Security-header behavior should be revalidated whenever browser features such as live video or approved camera capture are introduced, because a deliberately disabled feature may later require narrowly scoped permission.

---

# 20. Startup Guard & Readiness

Production startup should validate required configuration before claiming readiness.

Representative concerns:
- database configuration;
- secret configuration;
- HTTPS/cookie behavior;
- environment mode;
- integration readiness;
- production versus demo safety.

Health/readiness endpoints provide operational visibility but should not expose secrets.

---

# 21. Source Control & CI/CD

## GitHub
GitHub is the CrownPath source-code source of truth.

### Repository Rules
- no secrets committed;
- `.env` and private runtime configuration excluded;
- database files/backups excluded where appropriate;
- source changes versioned through commits;
- tests accompany security-sensitive changes.

## GitHub Actions
Automated CI is used to validate CrownPath code. PostgreSQL-backed testing is preferred for production-relevant database behavior.

### Release Confidence
A deployment should not be described as verified solely because a commit exists. Relevant tests and production deployment health should be checked.

---

# 22. Railway Production Architecture

Railway is the current authoritative CrownPath production hosting platform.

### Production Components
- CrownPath application service
- PostgreSQL service
- production environment configuration
- public application domain
- GitHub-triggered deployment flow

### Deployment Rule
Normal GitHub-main auto-deployment is preferred. Manual deployment-accept actions should not be used unnecessarily.

### Verification
After meaningful code changes:
1. confirm source commit;
2. confirm CI where applicable;
3. confirm Railway deployment success;
4. verify `/api/health` returns HTTP 200;
5. investigate logs if application health differs from deployment status.

---

# 23. Backup & Restore Architecture

Production backup/recovery should include:
- protected database backup;
- documented restore process;
- isolated restore testing;
- data-integrity verification;
- application connection verification;
- health check after restore;
- audit record of test results.

A backup that has never been restored successfully is not sufficient evidence of recovery readiness.

---

# 24. Audio Architecture

CrownPath models:
- stations;
- zones;
- playback devices;
- device-to-zone mapping;
- schedules;
- playback state;
- provider adapter.

### Preferred Direction
Business-authorized Pandora playback through a suitable business provider/device arrangement.

### Security/Terms Rule
CrownPath must not store a user's personal Pandora password. Provider/device integration remains disabled until an authorized business service and device configuration are supplied.

---

# 25. Live Classroom Architecture — Planned/Integration Layer

The CrownPath live-learning design anticipates a provider such as a WebRTC/LiveKit-class service for:
- instructor room access;
- learner room access;
- attendance;
- chat/Q&A;
- replay;
- multi-camera teaching;
- scheduled sessions;
- enrollment;
- time-zone handling.

### Boundary
Provider credentials and room-signing secrets belong in protected runtime configuration, never curriculum or public source documentation.

---

# 26. Email Integration — Planned/Configuration Layer

Email may support:
- verification;
- password reset;
- notifications;
- instructor workflow communication;
- approved learner communications.

Production email remains dependent on an authorized provider and protected credentials.

---

# 27. Payment Integration — Planned/Configuration Layer

Payment architecture may later support enrollment, products, services, subscriptions, or approved business functions.

### Requirements Before Activation
- selected authorized provider;
- server-side payment integration;
- protected credentials;
- webhook verification;
- transaction/audit handling;
- refund workflow;
- privacy/security review;
- clear separation between educational records and payment data.

CrownPath should avoid directly storing raw card credentials when a qualified payment provider can tokenize/host the sensitive payment flow.

---

# 28. Avatar & Bot Technical Architecture

Planned/expanding entities may include:
- Agent/Bot Profile
- Avatar Profile
- Agent Role
- Knowledge Scope
- Capability
- Tool Permission
- Course Assignment
- Lesson Assignment
- Language
- Voice
- Visual Style
- Safety Boundary
- Approval Status
- Audit Event

### Authorization Principle
A prompt is not a permission system. Every tool or record action must still pass server-side authorization.

### Knowledge Separation
Learner bots receive learner-safe curriculum. Instructor bots may receive restricted instructor material only when the authenticated instructor has the required permission.

### Human Gates
High-impact actions—publishing, credential decisions, regulatory claims, security changes, record alteration, external communications—require appropriate approval and audit controls.

---

# 29. Scalp Camera / Imaging Technical Boundary

Future image-analysis features should be designed as cosmetic documentation/education aids.

### Permitted Technical Outputs
- image quality checks;
- standardized capture guidance;
- visible-category assistance such as apparent flakes, dryness, oiliness, breakage, or buildup;
- before/after documentation;
- service-planning prompts;
- referral prompts.

### Prohibited Product Claims
- disease diagnosis;
- medical treatment recommendation;
- exact scalp pH inferred from an ordinary photograph;
- replacement for qualified clinical evaluation.

### Privacy Requirements
- consent;
- authorized storage;
- role-limited access;
- retention/deletion policy;
- audit where appropriate;
- no unnecessary identifying image content.

---

# 30. Logging, Monitoring & Audit

CrownPath should distinguish:

### Application Logs
Operational debugging and runtime events. Avoid writing secrets into logs.

### Security/Audit Events
High-value actions such as:
- role changes;
- Instructor approvals;
- protected record changes;
- publishing approvals;
- security-setting changes;
- Avatar/Bot permission changes;
- recovery actions.

### Monitoring
Operational monitoring should cover:
- application health;
- database connectivity;
- deployment failures;
- authentication anomalies;
- backup/recovery readiness;
- external integration status.

---

# 31. Error Handling Principles

- Return useful client errors without exposing stack traces or secrets.
- Treat authentication failures consistently.
- Distinguish unauthorized (authentication) from forbidden (authorization).
- Avoid revealing whether sensitive records exist when that information itself is restricted.
- Log enough context for authorized investigation without logging credentials.

---

# 32. Accessibility Architecture

Frontend and digital content should support progressive accessibility including:
- semantic markup;
- keyboard navigation;
- screen-reader labeling;
- captions/transcripts;
- text scaling;
- high contrast;
- reduced motion;
- multilingual content;
- text alternative to voice/avatar interaction.

Every printable lesson must remain usable without an Avatar/Bot.

---

# 33. Environment Variables & Secrets

Representative configuration categories may include:
- application secret;
- database URL;
- production/demo mode;
- HTTPS requirement;
- Owner activation configuration;
- provider integration credentials;
- email credentials;
- live-classroom credentials;
- payment credentials.

### Rules
1. Never commit real secrets to GitHub.
2. Never put secrets in printable manuals.
3. Use protected Railway/runtime environment configuration.
4. Rotate credentials after suspected exposure.
5. Grant provider credentials the minimum permissions required.

---

# 34. Testing Strategy

### Authentication
- registration restrictions;
- login success/failure;
- lockout;
- MFA challenge isolation;
- recovery codes;
- session expiration/revocation;
- password-change revocation.

### Authorization
- role permissions;
- Owner protections;
- Instructor workflow;
- object-level access;
- cross-track learner denial.

### Curriculum
- every catalog lesson resolves;
- learner content is sanitized;
- lesson steps remain stable;
- progress is idempotent;
- final step produces 100% completion.

### Production
- PostgreSQL compatibility;
- startup guard;
- health endpoint;
- deployment success;
- restore testing.

---

# 35. Technical Change Checklist

Before a significant change:
☐ Fetch current source
☐ Understand dependent tests/data
☐ Preserve backward-compatible lesson step IDs/order when progression depends on them
☐ Avoid unnecessary schema migrations
☐ Keep secrets out of source

After change:
☐ Run/verify relevant tests
☐ Review learner/instructor separation
☐ Review role authorization
☐ Verify deployment
☐ Verify health
☐ Update printable technical reference when architecture materially changes

---

# 36. Technical Handoff Checklist

A future CrownPath engineer should receive:
- GitHub repository access appropriate to role;
- architecture reference;
- environment-variable names without secret values;
- deployment procedure;
- database migration/backup procedure;
- CI test procedure;
- incident/recovery procedure;
- curriculum publication rules;
- learner/instructor separation rules;
- Avatar/Bot permission model;
- external-provider integration status;
- current regulatory-verification status.

The engineer should **not** receive passwords or secrets through this printable document.

---

# 37. Current Integration Status Categories

Use these labels rather than overstating readiness:

- **LIVE / VERIFIED** — implemented and checked in production.
- **IMPLEMENTED / CONFIGURATION REQUIRED** — code exists but external credentials/provider/device are still needed.
- **PLANNED** — architecture defined but implementation remains future work.
- **DISABLED FOR SAFETY** — intentionally unavailable until an approved configuration or review is complete.

### Integration Record

| Integration | Status | Last Verified | Owner/Engineer Notes |
|---|---|---|---|
| CrownPath web application | | | |
| PostgreSQL | | | |
| GitHub CI | | | |
| Railway deployment | | | |
| Email provider | | | |
| Live classroom provider | | | |
| Business audio provider/device | | | |
| Payment provider | | | |
| Scalp camera/AI | | | |
| Avatar/Bot runtime tools | | | |

---

# Technical Attestation

This reference documents CrownPath architecture without disclosing private credentials. Technical readiness must be based on implementation, tests, deployment verification, provider configuration, and applicable regulatory review—not on documentation alone.

**Technical reviewer:** ______________________________

**Version/date:** ___________________________________

**Signature/approval:** ______________________________
