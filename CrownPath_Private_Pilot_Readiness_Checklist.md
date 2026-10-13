# CrownPath Private Scalp-Care Pilot — Readiness Checklist

**Status:** Proposed, review only. **Do not invite testers until owner approval and all blocking checks are complete.**

This checklist implements [CrownPath_30_Day_Pilot_Validation_Plan.md](CrownPath_30_Day_Pilot_Validation_Plan.md). “Scalp Care Foundations” is the *pilot offer name*, not a literal lesson ID.

## Pilot curriculum mapping

| Track | Required core lesson | Optional guided practice |
|---|---|---|
| Barber | `barber-hair-scalp` — Hair & Scalp Science | `barber-scalp-camera-assessment` |
| Cosmetology | `cosmetology-hair-scalp` — Hair & Scalp Science | `cosmetology-scalp-camera-assessment` |

The pilot requires **one core lesson per tester**, matched to their professional track. The camera lesson supports **manual visible-observation practice only**, and must not be represented as automated diagnosis. If its instructions or consent flow are not ready, use a non-image written observation exercise instead. The pilot's separate safety knowledge check, feedback form, and manual exercise require human verification; API progress alone is not proof they were completed.

## Before invitations — owner-controlled gates

- [ ] Owner selects 5–10 invited testers, records anonymous participant codes CP-01 through CP-10, and approves pilot dates.
- [ ] Independent reviewer approves the learner-progress test changes in draft PR #39; do not merge automatically.
- [ ] Verify the pilot environment is isolated, has no production data or credentials, and can be reset safely.
- [ ] Confirm owner-authorized enrollment flags and role access **in the intended test environment only**. Never toggle production flags as part of this checklist.
- [ ] Manually verify registration, login, session expiry, sign-out, track-specific lesson access, and mobile navigation.
- [ ] Verify lesson completion and dashboard status for each track, including resume-after-sign-out.
- [ ] Verify no privileged self-registration, no duplicate-account bypass, and no cross-track lesson access.
- [ ] Verify learner-facing material does not expose answer keys or instructor-only notes.
- [ ] Display plain-language participation notice, voluntary consent, withdrawal option, photo handling/retention rules, and support contact before any photo collection.
- [ ] Obtain separate informed consent for any photo; avoid identifying features and unnecessary health details. No consent means no photo.
- [ ] Confirm secure photo handling, authorized access, deletion process, and no unapproved third-party AI upload.
- [ ] Validate “observe, continue, modify, stop, or refer” guidance with a qualified subject-matter reviewer. No medical diagnosis, inferred scalp pH, or treatment prescription.
- [ ] Prepare manual observation worksheet, safety questions/remediation, feedback form, and issue tracker.
- [ ] Record unresolved blockers; **any high-severity safety, privacy, access, or navigation issue blocks invitations**.
- [ ] Owner signs explicit **GO / NO-GO** decision for private invitations.

## Per-tester walkthrough

1. Assign participant code; explain voluntary participation and obtain required consent.
2. Register and sign in as BARBER or COSMETOLOGY_PRO in the isolated pilot environment.
3. Open the mapped Hair & Scalp Science lesson, finish each step, and confirm dashboard completion.
4. Complete manual scalp/hair observation (photo only with separate consent), using neutral visible descriptions.
5. Practice Continue / Modify / Stop / Refer and complete safety-critical knowledge questions.
6. Optionally open the mapped camera lesson if approved; check that opening it does not automatically mark it complete.
7. Complete the 11-question feedback form from the 30-day plan.
8. Record issue severity, corrective action, retest outcome, and any withdrawal or photo deletion request.

## Evidence and decision

Capture only participant code, role, lesson/exercise completion, safety outcome, feedback scores, willingness-to-use/recommend, and issue status. Keep any consent records and images separately under approved retention rules.

At the end of the 30 days, apply the success thresholds in the pilot plan (at least 5 completions; at least 80% of starters finish; clarity/usefulness averages at least 4/5; all pass safety-critical questions; at least 3 positive interest signals; zero unresolved high-severity issues). Owner records Proceed, Revise and Retest, or Pause/Pivot. **Passing CI is not a substitute for real-user testing or owner authorization.**

## Automated evidence available at drafting

Draft PR #39 contains isolated learner-progress, registration, and enrollment-gate tests. CI run #452 passed owner-access, application, and migration jobs. The tests are not yet merged and have not received independent review. This checklist does not enable a pilot, change release flags, merge code, or deploy anything.
