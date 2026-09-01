# CrownPath Instructor Edition
## Canonical Reconciliation Record

**Classification:** Instructor / Owner Restricted

**Purpose:** Mechanical reconciliation of instructor-facing assessment keys, rationales, progress steps, safety boundaries, and practical controls against CrownPath canonical lesson sources before final Instructor Edition publication.

> This record is not learner-facing. Never expose answer keys or rationales through Student Edition exports, learner APIs, learner avatars, public bots, or public course pages.

---

# Reconciliation Standard

For each lesson verify: lesson ID/pathway; progress-step wording/order; canonical knowledge-check answer and rationale; practical criteria; safety/scope boundary; bot restrictions; consistency with Instructor Edition; learner sanitization.

**Status:** MATCHED = consistent. EXPAND = consistent but final Instructor Edition should print additional canonical key/rationale detail. CORRECT = contradiction requiring repair.

---

# PASS 1 — COSMETOLOGY CORE, BEAUTY, WELLNESS & SHARED

## COS-4 — cosmetology-chemical-safety — MATCHED

Canonical answers/rationales:
1. Mixing ratio → **Manufacturer directions for the exact product system.** Exact manufacturer directions control preparation/use.
2. Passed preliminary test guarantees no reaction → **No.** Testing does not guarantee an adverse reaction is impossible.
3. Serious unexpected burning → **Stop and follow product immediate-response directions; escalate care when indicated.** Significant reactions require prompt safety action.

Canonical steps:
1. Read the full manufacturer instructions before mixing or applying.
2. Perform required consultation and preliminary testing.
3. Use ventilation, protection, timing, and application controls.
4. Stop, rinse, or escalate according to instructions if an adverse reaction occurs.

Safety controls: exact instructions, testing, PPE/ventilation, measurement/mixing, timing, monitoring, stop response, cleanup/documentation. Retain automatic remediation for invented ratios, improvised mixtures, exceeded processing limits, ignored reactions, or ignored instructor safety stops.

## COS-5 — cosmetology-hair-replacement — MATCHED

Canonical answers/rationales:
1. Outside course → **Implanting harvested follicles through skin incisions.** Surgical transplantation/implantation into living tissue is excluded.
2. Camera AI diagnoses hair-loss cause → **No; visible documentation only, not medical diagnosis.**
3. Attachment removal → **Manufacturer directions, lawful scope, and approved removal products.** Safe removal follows system instructions/scope, not force or improvisation.

Canonical steps:
1. Consult on goals, scalp condition, sensitivities, and system type.
2. Clean/prepare scalp and system according to product directions.
3. Use only lawful cosmetic attachment methods.
4. Explain maintenance, removal, sanitation, and follow-up.

Absolute boundary: no incision, graft harvesting, graft implantation, anesthesia, surgical transplantation, diagnosis, medication, or post-surgical medical management.

## COS-6 — cosmetology-makeup-artistry — EXPAND

Canonical answers/rationales:
1. Shared cream → **Dispense hygienically onto a clean palette when appropriate.** Reduces cross-contamination.
2. Severely irritated/injured intended area → **Postpone or modify and refer when appropriate.** Make a safety decision, not a diagnosis/concealment.
3. Corrective makeup → **Visual balancing using cosmetic color and placement.** Cosmetic technique changes visual balance, not anatomy/health status.

Canonical steps:
1. Consult on desired look, sensitivities, product history, visible skin condition.
2. Prepare sanitized tools/hygienic dispensing.
3. Apply complexion, color, eye, lip products in planned sequence.
4. Finish and explain safe removal/aftercare.

Existing Instructor Edition safety criteria are consistent; add all canonical questions/rationales to final detailed edition.

## COS-7 — cosmetology-nail-care — EXPAND

Canonical answers/rationales:
1. Scope-appropriate statement → **Visible change is outside cosmetic service; postpone and seek appropriate evaluation.** Describe visible findings without diagnosis.
2. Required single-use item → **Dispose according to required process.** Do not treat required single-use items as reusable.
3. Curing/removal → **Manufacturer directions and applicable rules.**

Canonical steps:
1. Consult/inspect visible nail and surrounding skin; prepare sanitized implements.
2. Shape/care without cutting living tissue beyond lawful scope.
3. Apply permitted products using directions/hygiene.
4. Clean/disinfect reusable implements/surfaces, dispose single-use items, explain home maintenance.

## COS-8 — wellness-massage-foundations — EXPAND

Canonical answers/rationales:
1. Completion automatically authorizes massage practice → **No.** Jurisdiction-specific licensing/scope must be independently satisfied.
2. Client withdraws consent → **Stop affected activity promptly and respect decision.** Consent is revocable throughout.
3. Outside general wellness lesson → **Claim that a technique will medically treat an injury.** Medical-treatment claims are outside scope.

Canonical steps:
1. Confirm purpose, preferences, boundaries, safety information.
2. Prepare clean/private environment; comfortable positioning/draping.
3. Use only techniques permitted by training, credential, jurisdiction while checking comfort.
4. End gradually; general non-medical aftercare; sanitize/document when required.

## COS-9 / Shared — wellness-fitness-foundations — EXPAND

Canonical answers/rationales:
1. Warm-up purpose → **Gradually prepare for activity.**
2. Progression → **Gradual changes while monitoring technique/recovery.**
3. Chest pain/fainting → **Stop and seek appropriate emergency/professional care.**

Canonical steps:
1. Appropriate warm-up/comfort check.
2. Controlled technique/gradual progression.
3. Recovery, hydration, sleep, general wellness habits.
4. Stop for concerning symptoms and seek appropriate care.

## Shared — wellness-client-experience — MATCHED

Canonical answers/rationales:
1. Handoff → **Only information needed for authorized continuity and safety.** Minimum necessary privacy/role boundaries.
2. Client asks to stop → **Respect request and stop or safely conclude.** Consent remains revocable.
3. Complaint → **Document facts, explain approved process, escalate when needed.**

Canonical steps:
1. Confirm booking details, goals, accessibility needs/preferences.
2. Explain service, experience, limits, price, aftercare before beginning.
3. Coordinate authorized handoffs while protecting privacy.
4. Collect feedback/document concerns/schedule appropriate follow-up without unsupported health claims.

## Shared — avatar-bot-builder-foundations — MATCHED

Canonical answers/rationales:
1. Protected-record permission → **Server-side authorization and approved capabilities.** Prompts do not grant authority.
2. Learner asks for instructor answers → **Refuse restricted material; continue permitted learning help.**
3. Unverified regulatory information → **Mark uncertainty and route for qualified human verification.**

Canonical steps:
1. Choose bot/avatar purpose.
2. Assign approved course areas, language, voice/text, role permissions.
3. Configure prohibited actions, escalation, privacy, human approval.
4. Test normal, uncertain, safety-sensitive, out-of-scope questions before publishing.

---

# PASS 2 — HOME CARE

Canonical source: crownpath/home_care_lesson_content.py

## HC-1 — home-care-foundations — MATCHED

Canonical answers/rationales:
1. Before unfamiliar task → **Confirm approved plan, training, and instructions.** Authorized instructions/role boundaries must be confirmed.
2. Factual statement → **The client coughed repeatedly during the visit and reported feeling short of breath.** It records observation/report without diagnosis.

Canonical steps:
1. Check environment for obvious hazards before beginning.
2. Explain task and obtain client cooperation.
3. Use clean hands and appropriate protective practices.
4. Document/report concerns according to organization procedures.

Instructor Edition keys and remediation approach match.

## HC-2 — home-care-sanitation — MATCHED

Canonical answers/rationales:
1. Gloves replace hand hygiene → **No.** Hand hygiene remains required at appropriate times and after glove removal.
2. Disinfecting-product use → **Label directions and applicable procedure.**

Canonical steps:
1. Clean hands before/after client-contact tasks.
2. Use gloves/protection when required.
3. Clean reusable work surfaces/equipment according to product directions.
4. Dispose of contaminated materials safely.

Instructor Edition matches and correctly prohibits invented chemical mixtures.

## HC-3 — home-care-communication — MATCHED

Canonical answers/rationales:
1. Unclear instruction → **Clarify and confirm before acting.**
2. Most factual report → **At 2:10 PM the client reported dizziness after standing; I helped them sit safely and notified the supervisor.** Records time, report, action, escalation without diagnosis.

Canonical steps:
1. Introduce yourself/explain purpose.
2. Listen without interrupting and confirm what you heard.
3. Limit private information to authorized people.
4. Use factual language when documenting/reporting.

Instructor Edition matches.

## HC-4 — home-care-documentation — MATCHED / FINAL DETAIL VERIFY

Canonical module confirms factual, timely documentation; separation of observation from opinion/diagnosis; authorized-service records; proper error correction; confidentiality; secure storage; incident/escalation handling. Existing Instructor Edition's appropriate-note example, authorized-system rule, and automatic remediation for false/deceptive/out-of-scope/private-record failures are consistent with the canonical module.

**Final publication action:** include the exact canonical HC-4 knowledge-check wording/rationales when assembling the fully detailed Instructor Edition. No contradiction identified.

---

# PASS 2 — BARBER CORE

Canonical source: crownpath/barber_core_lesson_content.py

## BAR-1 — barber-foundations — MATCHED

Canonical answers/rationales:
1. Inspect tools → **Before use.** Pre-service inspection identifies unsafe/damaged equipment before client contact.
2. Scope-appropriate consultation statement → **Visible flaking/redness; may need to modify or postpone service.** Neutral observation supports safe planning without diagnosis.

Canonical steps:
1. Sanitize station and prepare clean tools.
2. Discuss desired result and inspect visible hair/scalp condition.
3. Choose guards, combs, brushes, products appropriate to service.
4. Maintain tool control and client comfort throughout service.

Instructor Edition matches.

## BAR-4 — barber-cutting-grooming — MATCHED

Canonical answers/rationales:
1. Guide → **Provides a repeatable length reference.**
2. Perimeter detailing → **After major shape and blend are established.**
3. Hot clipper blade → **Stop contact and follow safe cooling/maintenance procedures.**

Canonical steps:
1. Establish shape, length, first guide.
2. Work methodically through sections/fade zones.
3. Cross-check balance and blend transitions.
4. Detail perimeter and finish according to consultation.

Instructor Edition keys, practical scoring, and isolated-skill remediation match.

## BAR-5 — barber-consultation-safety — MATCHED

Canonical answers/rationales:
1. Damaged electrical equipment → **Remove from service and follow repair/replacement procedures.**
2. Out-of-scope visible scalp concern → **Describe concern neutrally, postpone service, recommend appropriate evaluation.**
3. Disinfectant contact time → **Follow label directions; it is part of proper product use.**

Canonical steps:
1. Confirm desired style and relevant service history.
2. Check tools, cords, surfaces, client protection.
3. Monitor comfort and stop for unexpected reaction.
4. Clean, disinfect, store tools, reset workstation.

Instructor Edition matches.

---

# PASS 2 — ADVANCED HAIR/SCALP & CAMERA/AI

Canonical source: crownpath/advanced_lesson_content.py

## COS-2 — cosmetology-hair-scalp — EXPAND

Canonical answers/rationales:
1. Scalp pH from photo alone → **No; appearance alone does not provide a reliable chemical pH measurement.** pH is a chemical property and must not be fabricated from appearance.
2. Scope-appropriate observation → **Visible flaking/redness; postpone and seek appropriate evaluation.** Describe visible finding and safe decision without diagnosis.
3. Conditioner goal for visibly dry/damaged hair → **Improve manageability, slip, feel, or protection according to product directions.** Cosmetic benefit, not diagnosis/cure.

Canonical steps:
1. Observe hair/scalp under good lighting.
2. Ask about prior services, sensitivities, product reactions.
3. Choose techniques based on condition/service goals.
4. Refer suspected medical conditions rather than diagnosing.

Existing Instructor Edition boundaries match; final detailed edition should print all canonical keys/rationales.

## COS-3 — cosmetology-scalp-camera-assessment — EXPAND

Canonical answers/rationales:
1. AI sees pattern with several causes → **Flag visible pattern for human review and stay within cosmetic language.** AI supports observation, not diagnosis.
2. Consistent lighting/distance → **Make images comparable over time.** Standardization improves useful visual comparison.

Canonical steps:
1. Explain imaging/privacy and obtain permission.
2. Capture comparable views with clean equipment/consistent lighting.
3. Record objective visible observations and relevant client-reported history.
4. Use findings for cosmetic conditioning/cleansing/protective-care/referral options within scope.

Instructor Edition safety-critical checkoff matches. Add exact canonical questions/rationales in final detailed edition.

## BAR-2 — barber-hair-scalp — EXPAND

Canonical module confirms: texture/density/growth analysis; neutral visible scalp observation; dryness/damage and conditioning; product selection; exact-pH-from-image prohibition; proceed/modify/postpone-refer decision pathway. Existing Instructor Edition teaching emphasis and pH/diagnosis boundaries are consistent.

**Final publication action:** insert exact canonical Barber Hair & Scalp knowledge-check wording/rationales from the canonical module into the detailed Instructor Edition. No contradiction identified.

## BAR-3 — barber-scalp-camera-assessment — EXPAND

Canonical advanced module uses the same governing safety pattern: consent/privacy, standardized capture, neutral visible observation, AI as a human-review aid, no diagnosis, no exact pH from image, referral for out-of-scope findings. Existing Instructor Edition safety-critical checkoff is consistent.

**Final publication action:** include exact canonical Barber Scalp Camera assessment questions/rationales in detailed edition. No contradiction identified.

---

# PASS 2 — COSMETOLOGY FOUNDATION FALLBACK

Canonical source: crownpath/lesson_content.py

## COS-1 — cosmetology-foundations — MATCHED

Canonical answers/rationales:
1. Scope-appropriate statement → **I can see visible redness and flaking, so I recommend postponing and seeking appropriate evaluation.** Learners may describe visible findings and make safe decisions without diagnosis.
2. Professional product use → **Manufacturer directions and applicable rules.** These control product use.

Canonical progress steps:
1. Sanitize the station and assemble clean tools.
2. Discuss goals, history, sensitivities, and visible hair/scalp condition.
3. Select the service plan and products within scope of practice.
4. Complete the service, sanitation, and client-care instructions.

Instructor Edition matches. Canonical instructor notes require cosmetic-observation-versus-diagnosis distinction and current jurisdiction-specific verification before representing licensure credit.

---

# LEARNER ANSWER-KEY PROTECTION — VERIFIED ARCHITECTURALLY

Canonical source: crownpath/lesson_content.py

Instructor-only keys are explicitly identified as:
- answer_index
- rationale
- instructor_notes
- answer_key
- instructor_answer_key
- correct_answer

The learner content path recursively removes these fields before returning a deep-copied learner-safe lesson. Canonical instructor metadata remains server-side through the trusted canonical-content path.

**Status:** Architecture is correctly designed to keep instructor answers out of learner-facing lesson content. Final publication and API testing should continue to verify this invariant.

---

# FINAL RECONCILIATION FINDINGS

## MATCHED
- Home Care Foundations
- Home Care Sanitation
- Home Care Communication
- Barber Foundations
- Barber Cutting/Grooming
- Barber Consultation/Safety
- Cosmetology Foundations
- Chemical Safety
- Non-Surgical Hair Replacement
- Client Experience
- Avatar/Bot Builder

## CONSISTENT — EXPAND WITH FULL CANONICAL KEYS/RATIONALES
- Home Care Documentation
- Barber Hair & Scalp
- Barber Scalp Camera/AI
- Cosmetology Hair & Scalp
- Cosmetology Scalp Camera/AI
- Makeup Artistry
- Nail Care
- Wellness Massage
- Fitness/Recovery

## CONTRADICTIONS
**None identified in the reviewed Instructor Edition against the canonical modules.**

---

# NEXT PUBLICATION ACTION

1. Fetch the latest full `docs/CrownPath_Instructor_Edition_Printable.md`.
2. Expand every EXPAND section with exact canonical assessment keys/rationales.
3. Preserve all existing safety-critical practical scoring/remediation rules.
4. Keep Instructor/Owner classification and answer-key restrictions prominent.
5. Verify learner-facing curriculum remains sanitized.
6. Generate the detailed Instructor Edition PDF.
7. Render and visually inspect every page before publication.

---

# Reconciliation Attestation

**Record:** CrownPath Instructor Canonical Reconciliation

**Passes completed:**
- Pass 1 — Cosmetology Core, Beauty, Wellness, Client Experience, Avatar/Bot
- Pass 2 — Home Care, Barber Core, Advanced Hair/Scalp & Camera/AI, Cosmetology Foundations

**Result:** Canonical reconciliation is complete at the curriculum-source level. No contradictions were identified. The final Instructor Edition now needs the documented canonical detail expansions before authoritative printable PDF publication.
