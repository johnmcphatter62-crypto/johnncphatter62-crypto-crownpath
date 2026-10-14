# CrownPath — Non-Photo Lab Learner-Progress Integration Review

**2026-10-14 · Source-backed review only · No runtime changes**

## Source mapping

Inspected `crownpath/main.py` on `main`.

- BARBER catalog includes `barber-hair-scalp`; COSMETOLOGY_PRO includes `cosmetology-hair-scalp`.
- `lesson_for_role` restricts lesson IDs to the role's catalog and loads content via `get_lesson_content`.
- `POST /api/learner/lessons/{lesson_id}/open` creates or updates progress and returns content, completed steps, and total steps.
- `POST /api/learner/lessons/{lesson_id}/steps/{step_index}/complete` marks a valid step complete and recalculates progress.
- `POST /api/learner/lessons/{lesson_id}/complete` marks **every step complete** in a single request. In the inspected code it does **not** require submission or grading of the lab's three safety-critical exit questions.

## Integration recommendation

Treat the new [non-photo lab](CrownPath_Non_Photo_Scalp_Observation_Classroom_Lab.md) as an **instructor-led exercise and paper checkoff** mapped to the two existing hair/scalp lessons. Do not claim the platform enforces its safety quiz.

Before online safety certification or a pilot completion claim, independently design and review:
1. Explicit rubric and recorded instructor checkoff for all three safety-critical answers, including remediation.
2. Authorization and cross-learner isolation for checkoff results.
3. Separate distinction between a generic lesson progress percentage and safety qualification.
4. An isolated synthetic test proving `/complete` alone cannot be misrepresented as safety-checkoff success.
5. Accessible text-only completion without camera/photo data.

## Suggested isolated tests (not executed)

| Test | Setup | Expected |
|---|---|---|
| NP-01 | Synthetic BARBER account opens `barber-hair-scalp` | Lesson loads, progress tracked |
| NP-02 | Synthetic COSMETOLOGY_PRO opens `cosmetology-hair-scalp` | Lesson loads, progress tracked |
| NP-03 | BARBER attempts cosmetology lesson | Denied by role catalog |
| NP-04 | Invalid step index | 404, no progress mutation |
| NP-05 | Repeat step completion | Idempotent, no duplicate step |
| NP-06 | Complete lesson without quiz | Generic progress may become 100%; **must not be called safety checkoff PASS** |
| NP-07 | No photo/camera available | Paper-based lab still possible |
| NP-08 | Safety-critical answer incorrect | Instructor withholds lab checkoff; remediation documented manually |

**Gate:** No automatic certificate, safety credential, or pilot pass claim until a separately reviewed assessment workflow exists. All tests require an authorized isolated environment and synthetic accounts. Do not enable enrollment, merge, deploy, or invite real participants based on this document.
