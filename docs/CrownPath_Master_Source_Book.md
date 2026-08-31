# CrownPath Master Source Book

**Status:** Working master record for printable curriculum, instructor materials, student materials, operating controls, and technical reference.

## Purpose

The CrownPath Master Source Book is the printable master record of the CrownPath program. It organizes the curriculum and operating model into a form that can be reviewed, printed, exported to PDF, and maintained alongside the live software platform.

This source book does **not** itself certify regulatory credit, create professional licensure, or replace official jurisdiction-specific requirements. Any State Board, licensing, continuing-education, clinical, or regulated-credit claim must be independently verified from the applicable official source before publication.

## Publication Layers

CrownPath maintains separate publication layers so restricted material is not exposed to learners.

1. **Student Edition** — lesson summaries, learning objectives, instructional sections, demonstrations, guided practice, learner-facing knowledge checks without answer keys, practical checkoff expectations, student handouts, safety notes, and printable worksheets.
2. **Instructor Edition** — Student Edition material plus instructor notes, answer keys, rationales, demonstration guidance, assessment administration notes, practical scoring guidance, remediation notes, and instructor-only operational guidance.
3. **Owner / Operations Edition** — governance, approvals, roles and permissions, security controls, audit and recovery procedures, regulatory verification workflows, business operations, content publishing controls, Avatar/Bot governance, and technical handoff records.
4. **Technical Source Reference** — architecture, APIs, data model, deployment, backup/recovery, CI/CD, integrations, security controls, and source-code reference. Secrets and private credentials are excluded.

## Volume I — CrownPath Program & Operating Model

### 1. CrownPath Mission and Program Overview
- CrownPath purpose and learner pathways
- CrownPath Core operating model
- Solar System architecture metaphor
- Human Body communication and feedback metaphor
- Automobile execution and control metaphor
- Core cycle: CORE → SIGNAL → ACTION → FEEDBACK → PROTECTION → DIAGNOSTICS → CORRECTION

### 2. Roles, Permissions, and Human Oversight
- Owner
- Instructor
- Home Care learner
- Barber learner
- Cosmetology learner
- Role-based permissions
- Instructor approval workflow
- Human approval requirements
- Safety-sensitive decision boundaries

### 3. Learning Delivery System
- Digital lessons
- Live classroom
- Video and replay
- 3D models and animation
- Practical labs and checkoffs
- Attendance and progress tracking
- Printables
- Accessibility and multilingual delivery
- Avatar and Bot learning assistance

### 4. Regulatory and Scope Framework
- State-by-state rules framework
- Official-source verification requirements
- Practice versus official-credit distinction
- Scope-of-practice boundaries
- Regulatory evidence vault
- Inspection and audit preparation

## Volume II — Home Care Pathway

### HC-1. Client Safety & Home Care Foundations
Source lesson ID: `home-care-foundations`

### HC-2. Sanitation & Infection Control
Source lesson ID: `home-care-sanitation`

### HC-3. Professional Communication
Source lesson ID: `home-care-communication`

### HC-4. Care Documentation
Source lesson ID: `home-care-documentation`

### HC-5. Wellness Client Experience & Professional Boundaries
Source lesson ID: `wellness-client-experience`

### HC-6. CrownPath Avatar & Bot Builder Foundations
Source lesson ID: `avatar-bot-builder-foundations`

## Volume III — Barber Pathway

### BAR-1. Barbering Foundations
Source lesson ID: `barber-foundations`

### BAR-2. Hair & Scalp Science
Source lesson ID: `barber-hair-scalp`

### BAR-3. Scalp Camera & AI-Assisted Cosmetic Assessment
Source lesson ID: `barber-scalp-camera-assessment`

### BAR-4. Cutting, Fading & Grooming
Source lesson ID: `barber-cutting-grooming`

### BAR-5. Client Consultation & Shop Safety
Source lesson ID: `barber-consultation-safety`

### BAR-6. Beauty & Wellness Client Experience
Source lesson ID: `wellness-client-experience`

### BAR-7. Fitness, Recovery & General Wellness Foundations
Source lesson ID: `wellness-fitness-foundations`

### BAR-8. CrownPath Avatar & Bot Builder Foundations
Source lesson ID: `avatar-bot-builder-foundations`

## Volume IV — Cosmetology, Beauty & Wellness Pathway

### COS-1. Cosmetology Foundations
Source lesson ID: `cosmetology-foundations`

### COS-2. Hair & Scalp Science
Source lesson ID: `cosmetology-hair-scalp`

### COS-3. Scalp Camera & AI-Assisted Cosmetic Assessment
Source lesson ID: `cosmetology-scalp-camera-assessment`

### COS-4. Chemical Services & Product Safety
Source lesson ID: `cosmetology-chemical-safety`

### COS-5. Non-Surgical Hair Replacement & Scalp Application
Source lesson ID: `cosmetology-hair-replacement`

### COS-6. Professional Makeup Artistry
Source lesson ID: `cosmetology-makeup-artistry`

### COS-7. Manicure & Pedicure Nail Care
Source lesson ID: `cosmetology-nail-care`

### COS-8. Wellness Massage Foundations & Scope Awareness
Source lesson ID: `wellness-massage-foundations`

### COS-9. Fitness, Recovery & General Wellness Foundations
Source lesson ID: `wellness-fitness-foundations`

### COS-10. Integrated Beauty & Wellness Client Experience
Source lesson ID: `wellness-client-experience`

### COS-11. CrownPath Avatar & Bot Builder Foundations
Source lesson ID: `avatar-bot-builder-foundations`

## Volume V — Avatar & Bot Builder

### 1. Avatar/Bot Roles
- Learner Guide
- Instructor Assistant
- Demonstration Coach
- Client Service Assistant
- Owner/Admin Assistant
- Content Assistant
- Regulatory Research Assistant
- Accessibility/Translation Assistant

### 2. Builder Configuration
- Name and identity
- Visual avatar style
- Voice and language
- Approved knowledge sources
- Course/pathway assignment
- Capabilities and tool permissions
- Prohibited actions
- Escalation rules
- Approval and publishing status

### 3. Safety & Governance
- Least privilege
- Server-side authorization
- Learner/instructor content separation
- Privacy boundaries
- Human review
- Regulatory and medical restrictions
- Audit logging
- Versioning
- Red-team and adversarial testing

## Volume VI — Instructor Manual

For each lesson, the Instructor Edition will include:
- Lesson purpose and scope
- Estimated instructional time
- Prerequisites
- Materials
- Learning objectives
- Full lesson sections
- Demonstration instructions
- Guided-practice activities
- Knowledge-check answer keys and rationales
- Practical checkoff rubric
- Instructor notes
- Remediation and repeat-practice guidance
- Safety and referral boundaries
- Printable instructor checklist

**Instructor-only material must never be included in learner-facing API responses or Student Edition exports.**

## Volume VII — Student Workbook & Printables

For each learner lesson:
- Lesson title
- Summary
- Learning objectives
- Key concepts
- Step-by-step service or learning sequence
- Demonstration observation sheet
- Guided-practice worksheet
- Knowledge check without answers
- Practical checkoff expectations
- Student handout
- Notes page
- Safety and scope reminder

## Volume VIII — Client, Salon, Barber Shop & Wellness Operations

- Client journey
- Consultation and consent
- Scalp imaging permission/privacy
- Service documentation
- Sanitation workflows
- Complaints and service recovery
- Feedback and follow-up
- Audio zones and business music controls
- Inventory and consumables
- Staff roles and credential awareness
- Accessibility practices

## Volume IX — Security, Privacy & Recovery

- Authentication
- MFA
- Recovery codes
- Server-side sessions
- Session revocation
- Password-reset session revocation
- Role permissions
- Object-level authorization
- Audit records
- Security headers
- Backup and restore
- Incident recovery
- Environment separation
- Secret handling

## Volume X — Technical Architecture & Deployment

- FastAPI backend
- HTML/CSS/JavaScript frontend
- SQLAlchemy
- PostgreSQL production database
- SQLite development/demo use
- GitHub source control
- CI testing
- Railway production deployment
- API architecture
- Data models
- Deployment configuration
- Health/readiness checks
- Integration adapters
- Technical source-code reference

## Print Production Rules

- Student exports must be generated from learner-safe content only.
- Instructor exports may include answer keys and instructor notes only in clearly marked Instructor Edition sections.
- Owner/Operations material must not contain passwords, API keys, MFA secrets, database credentials, payment credentials, or private service credentials.
- Regulatory claims must be dated and sourced to official authorities before being labeled current or approved.
- Medical diagnosis, treatment, surgical implantation, anesthesia, graft harvesting, and other medical procedures remain outside CrownPath cosmetic education unless a separately qualified and legally authorized program is created and independently reviewed.
- Every printable lesson should remain understandable without requiring an Avatar or Bot.

## Build Status Checklist

- [x] Home Care curriculum expanded
- [x] Barber curriculum expanded
- [x] Cosmetology hair/scalp curriculum expanded
- [x] Scalp Camera/AI education expanded
- [x] Chemical Safety expanded
- [x] Non-Surgical Hair Replacement expanded
- [x] Makeup Artistry expanded
- [x] Nail Care expanded
- [x] Wellness Massage expanded
- [x] Fitness Foundations expanded
- [x] Client Experience expanded
- [x] Avatar & Bot Builder expanded
- [x] Learner answer-key protection implemented
- [ ] Generate Student Edition printable lesson pages
- [ ] Generate Instructor Edition printable lesson pages
- [ ] Generate practical checkoff forms
- [ ] Generate student worksheets and note pages
- [ ] Generate Owner/Operations printables
- [ ] Generate Technical Source Reference
- [ ] Assemble final PDF Master Source Book
- [ ] Final regulatory-source review before any official-credit claims
