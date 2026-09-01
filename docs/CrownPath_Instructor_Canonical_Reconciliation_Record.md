# CrownPath Instructor Edition
## Canonical Reconciliation Record

**Classification:** Instructor / Owner Restricted

**Purpose:** Record the mechanical reconciliation of instructor-facing assessment keys, rationales, safety boundaries, and practical controls against CrownPath canonical lesson sources before final Instructor Edition PDF publication.

> This record is not learner-facing. Do not expose answer keys through Student Edition exports, learner APIs, learner avatars, public bots, or public course pages.

---

# Reconciliation Standard

For each canonical lesson, verify:
1. lesson ID and pathway placement;
2. learner progress-step wording/order;
3. knowledge-check question;
4. canonical `answer_index` and corresponding answer text;
5. canonical rationale;
6. practical-checkoff criteria;
7. safety note/scope boundary;
8. Avatar/Bot prohibited actions;
9. instructor manual wording does not contradict canonical source;
10. learner-facing material remains free of answer keys/rationales.

**Status labels:**
- **MATCHED** — instructor wording is consistent with canonical source.
- **EXPAND** — instructor material is directionally correct but should include the canonical key/rationale in the final detailed Instructor publication.
- **CORRECT BEFORE FINAL PDF** — mismatch requiring correction.

---

# COSMETOLOGY CORE — CANONICAL CHECK

Canonical source reviewed: `crownpath/cosmetology_core_lesson_content.py`

## COS-4 — `cosmetology-chemical-safety`

### Canonical Knowledge Check 1
**Question:** What controls the mixing ratio for a professional chemical product?

**Correct answer:** Manufacturer directions for the exact product system.

**Canonical rationale:** The exact manufacturer's directions control product preparation and use.

**Instructor Edition:** Matches.

**Status:** **MATCHED**

### Canonical Knowledge Check 2
**Question:** Does a passed preliminary test guarantee that no reaction can occur?

**Correct answer:** No.

**Canonical rationale:** Required tests reduce risk or screen for specified concerns but do not guarantee that an adverse reaction is impossible.

**Instructor Edition:** Matches.

**Status:** **MATCHED**

### Canonical Knowledge Check 3
**Question:** What should happen when a client reports a serious unexpected burning sensation during processing?

**Correct answer:** Stop and follow the product's immediate-response directions, escalating care when indicated.

**Canonical rationale:** Unexpected significant reactions require prompt safety action, not stronger or longer processing.

**Instructor Edition:** Matches.

**Status:** **MATCHED**

### Canonical Progress Steps
1. Read the full manufacturer instructions before mixing or applying.
2. Perform required consultation and preliminary testing.
3. Use ventilation, protection, timing, and application controls.
4. Stop, rinse, or escalate according to instructions if an adverse reaction occurs.

### Safety-Critical Canonical Controls
- Exact manufacturer instructions.
- Required testing.
- PPE and ventilation.
- Correct measurement/mixing.
- Correct timing.
- Client-response monitoring.
- Stop-response procedure.
- Cleanup/documentation.

**Final publication note:** Retain instructor automatic-stop rules against invented ratios, improvised mixtures, exceeded processing limits, ignored adverse reactions, and ignored instructor safety stops.

---

## COS-5 — `cosmetology-hair-replacement`

### Canonical Knowledge Check 1
**Question:** Which procedure is outside CrownPath's non-surgical hair-replacement course?

**Correct answer:** Implanting harvested follicles through skin incisions.

**Canonical rationale:** Surgical transplantation and implantation into living tissue are medical procedures and are excluded.

**Instructor Edition:** Matches.

**Status:** **MATCHED**

### Canonical Knowledge Check 2
**Question:** Can scalp-camera AI diagnose the cause of a client's hair loss?

**Correct answer:** No; it may support visible documentation but not medical diagnosis.

**Canonical rationale:** Visible imaging support does not establish a medical diagnosis.

**Instructor Edition:** Matches.

**Status:** **MATCHED**

### Canonical Knowledge Check 3
**Question:** What should control removal of an adhesive or attachment system?

**Correct answer:** Manufacturer directions, lawful scope, and appropriate approved removal products.

**Canonical rationale:** Safe removal follows the system instructions and professional scope rather than force or improvisation.

**Instructor Edition:** Matches.

**Status:** **MATCHED**

### Canonical Progress Steps
1. Consult on goals, scalp condition, sensitivities, and the type of hair-replacement system.
2. Clean and prepare the scalp and system according to product directions.
3. Use only cosmetic attachment methods that are lawful within the practitioner's scope.
4. Explain maintenance, removal, sanitation, and follow-up care.

### Absolute Course Boundary
No incision, graft harvesting, graft placement/implantation into living tissue, anesthesia, surgical transplantation, medical diagnosis, medication, or post-surgical medical management.

---

# BEAUTY — CANONICAL CHECK

Canonical source reviewed: `crownpath/beauty_lesson_content.py`

## COS-6 — `cosmetology-makeup-artistry`

### Canonical Knowledge Check 1
**Question:** What is the safest approach to a shared cream product?

**Correct answer:** Dispense product hygienically onto a clean palette when appropriate.

**Rationale:** Hygienic dispensing helps reduce cross-contamination.

### Canonical Knowledge Check 2
**Question:** What should a cosmetology learner do when the intended makeup area appears severely irritated or injured?

**Correct answer:** Postpone or modify the service and refer when appropriate.

**Rationale:** Unsafe or out-of-scope findings require a safety decision rather than diagnosis or concealment.

### Canonical Knowledge Check 3
**Question:** Corrective makeup primarily means what?

**Correct answer:** Visual balancing using cosmetic color and placement.

**Rationale:** Corrective cosmetic technique changes visual balance, not anatomy or health status.

**Instructor Edition status:** Existing teaching and safety criteria are consistent, but the detailed final Instructor Edition should explicitly include all three canonical assessment keys/rationales.

**Status:** **EXPAND**

### Canonical Progress Steps
1. Consult on desired look, sensitivities, product history, and visible skin condition.
2. Prepare sanitized tools and hygienic product-dispensing methods.
3. Apply complexion, color, eye and lip products in a planned sequence.
4. Finish the look and explain safe removal and aftercare.

---

## COS-7 — `cosmetology-nail-care`

### Canonical Knowledge Check 1
**Question:** Which statement stays within cosmetic nail-care scope?

**Correct answer:** “I see a visible change that is outside this cosmetic service, so I recommend postponing and seeking appropriate evaluation.”

**Rationale:** The learner may describe visible findings and make a safe service decision without diagnosis.

### Canonical Knowledge Check 2
**Question:** What should happen to a single-use item after the service when applicable rules require disposal?

**Correct answer:** Dispose of it according to the required process.

**Rationale:** Single-use items must not be treated as reusable when rules or manufacturer directions require disposal.

### Canonical Knowledge Check 3
**Question:** What controls curing or removal of a cosmetic nail product?

**Correct answer:** Manufacturer directions and applicable rules.

**Rationale:** Product systems should be used according to their instructions and applicable requirements.

**Instructor Edition status:** Existing teaching/safety criteria are consistent; detailed assessment section needs canonical questions/rationales added.

**Status:** **EXPAND**

### Canonical Progress Steps
1. Consult, inspect visible nail and surrounding skin condition, and prepare sanitized implements.
2. Shape and care for nails and surrounding cosmetic areas without cutting living tissue beyond lawful scope.
3. Apply permitted cosmetic products using manufacturer directions and hygienic practices.
4. Clean and disinfect reusable implements and surfaces, dispose of single-use items, and explain home maintenance.

---

# WELLNESS — CANONICAL CHECK

Canonical source reviewed: `crownpath/wellness_lesson_content.py`

## COS-8 — `wellness-massage-foundations`

### Canonical Knowledge Check 1
**Question:** Does completing this CrownPath unit automatically authorize a learner to practice massage therapy?

**Correct answer:** No; licensing and scope requirements vary and must be independently satisfied.

**Rationale:** Educational completion does not replace jurisdiction-specific licensing or credential requirements.

### Canonical Knowledge Check 2
**Question:** What should happen if a client withdraws consent during a wellness service?

**Correct answer:** Stop the affected activity promptly and respect the client's decision.

**Rationale:** Client consent remains active and revocable throughout the service.

### Canonical Knowledge Check 3
**Question:** Which claim is outside this general wellness lesson?

**Correct answer:** “This technique will medically treat your injury.”

**Rationale:** Medical treatment claims are outside the unit's non-medical wellness scope.

**Instructor Edition status:** Existing scope/stop rules are consistent; detailed final edition should add all canonical keys/rationales.

**Status:** **EXPAND**

### Canonical Progress Steps
1. Confirm the service purpose, client preferences, boundaries, and relevant safety information.
2. Prepare a clean, private environment and position the client comfortably with appropriate draping.
3. Use only techniques permitted by the practitioner's training, credential, and jurisdiction while continually checking comfort.
4. End gradually, provide general non-medical aftercare guidance, sanitize the area, and document the service when required.

---

## COS-9 / Shared — `wellness-fitness-foundations`

### Canonical Knowledge Check 1
**Question:** What is the main purpose of a warm-up?

**Correct answer:** Gradually prepare for activity.

**Rationale:** A warm-up prepares the body gradually rather than exhausting it.

### Canonical Knowledge Check 2
**Question:** Which progression approach best fits this course?

**Correct answer:** Use gradual changes while monitoring technique and recovery.

**Rationale:** Gradual progression supports safer learning and adaptation.

### Canonical Knowledge Check 3
**Question:** What should a participant do for chest pain or fainting during activity?

**Correct answer:** Stop activity and seek appropriate emergency or professional care.

**Rationale:** Serious warning signs require stopping and appropriate care.

**Instructor Edition status:** Existing instructor exercise/boundary is consistent; detailed final edition should add canonical keys/rationales.

**Status:** **EXPAND**

### Canonical Progress Steps
1. Begin with an appropriate warm-up and assess comfort before increasing effort.
2. Use controlled technique and gradual progression rather than sudden overload.
3. Include recovery, hydration, sleep, and general wellness habits as part of the routine.
4. Stop activity for concerning symptoms and seek appropriate professional or emergency care when indicated.

---

# CLIENT EXPERIENCE — CANONICAL CHECK

Canonical source reviewed: `crownpath/experience_agent_lesson_content.py`

## Shared — `wellness-client-experience`

### Canonical Knowledge Check 1
**Question:** What should be shared during a professional handoff?

**Correct answer:** Only information needed for authorized continuity and safety.

**Rationale:** Handoffs should follow minimum-necessary privacy and role boundaries.

### Canonical Knowledge Check 2
**Question:** What should happen when a client asks to stop a service?

**Correct answer:** Respect the request and stop or safely conclude the service.

**Rationale:** Consent remains active and revocable during the service.

### Canonical Knowledge Check 3
**Question:** Which complaint response is appropriate?

**Correct answer:** Document facts, explain the approved process, and escalate when needed.

**Rationale:** Professional service recovery follows authority, documentation, and escalation rules.

**Instructor Edition:** All three existing keys match.

**Status:** **MATCHED**

### Canonical Progress Steps
1. Confirm booking details, service goals, accessibility needs, and relevant preferences.
2. Explain each service, expected experience, limits, price, and aftercare before beginning.
3. Coordinate handoffs between authorized professionals while protecting client privacy.
4. Collect feedback, document concerns, and schedule appropriate follow-up without making unsupported health claims.

---

# AVATAR & BOT BUILDER — CANONICAL CHECK

Canonical source reviewed: `crownpath/experience_agent_lesson_content.py`

## Shared — `avatar-bot-builder-foundations`

### Canonical Knowledge Check 1
**Question:** What actually grants a CrownPath bot permission to change a protected record?

**Correct answer:** Server-side authorization and approved capabilities.

**Rationale:** Permissions must be enforced by the system, not by prompt wording.

### Canonical Knowledge Check 2
**Question:** What should a learner bot do when asked for instructor-only quiz answers?

**Correct answer:** Refuse to expose restricted material and continue with permitted learning help.

**Rationale:** Learner-facing bots must not expose instructor-only answer keys.

### Canonical Knowledge Check 3
**Question:** What should a regulatory research bot do when official information is uncertain or not yet human-verified?

**Correct answer:** Clearly mark uncertainty and route it for qualified human verification.

**Rationale:** Regulatory conclusions require verified sources and appropriate human review.

**Instructor Edition:** All three existing keys match.

**Status:** **MATCHED**

### Canonical Progress Steps
1. Choose the avatar or bot purpose, such as learner guide, instructor assistant, client helper, or Owner support.
2. Assign the approved course areas, language, voice or text mode, and role-based permissions.
3. Configure prohibited actions, escalation rules, privacy limits, and human-approval requirements.
4. Test the avatar or bot against normal, uncertain, safety-sensitive, and out-of-scope questions before publishing.

---

# Reconciliation Findings — This Pass

## Confirmed Matches
- Chemical Safety assessment keys.
- Non-Surgical Hair Replacement assessment keys.
- Client Experience assessment keys.
- Avatar/Bot Builder assessment keys.
- Core safety boundaries for makeup, nail care, massage, and fitness.

## Detailed Instructor Expansion Required
The current Instructor Edition is consistent but does not yet print every canonical assessment question/rationale for:
- Makeup Artistry;
- Nail Care;
- Wellness Massage;
- Fitness/Recovery.

These should be expanded before the detailed Instructor PDF is called authoritative.

## No Contradiction Found in This Pass
No reviewed instructor statement contradicts the canonical source modules above.

---

# Remaining Reconciliation Before Final Instructor PDF

The following canonical sources must still be mechanically checked in the same manner:
- `crownpath/home_care_lesson_content.py`
- `crownpath/barber_core_lesson_content.py`
- Barber sections of `crownpath/advanced_lesson_content.py`
- Cosmetology hair/scalp and scalp-camera sections of `crownpath/advanced_lesson_content.py`
- canonical/fallback `cosmetology-foundations` content in `crownpath/lesson_content.py`

After those checks:
1. update `docs/CrownPath_Instructor_Edition_Printable.md` with every canonical key/rationale;
2. preserve instructor-only classification;
3. verify learner APIs/materials remain sanitized;
4. generate the detailed Instructor PDF;
5. visually inspect every PDF page before publication.

---

# Reconciliation Attestation

**Record:** CrownPath Instructor Canonical Reconciliation

**Pass:** 1 — Cosmetology Core, Beauty, Wellness, Client Experience, Avatar/Bot

**Result:** Reviewed modules are consistent with the Instructor Edition; identified expansion items must be incorporated before final authoritative Instructor PDF publication.
