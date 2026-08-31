from copy import deepcopy

from crownpath.advanced_lesson_content import get_advanced_lesson_content
from crownpath.beauty_lesson_content import get_beauty_lesson_content
from crownpath.wellness_lesson_content import get_wellness_lesson_content
from crownpath.experience_agent_lesson_content import get_experience_agent_lesson_content
from crownpath.cosmetology_core_lesson_content import get_cosmetology_core_lesson_content
from crownpath.barber_core_lesson_content import get_barber_core_lesson_content
from crownpath.home_care_lesson_content import get_home_care_lesson_content


FOUNDATION_LESSON_CONTENT = {
    "cosmetology-foundations": {
        "summary": "Build a professional cosmetology service from consultation through sanitation, client protection, service planning, completion, and follow-up.",
        "scope": "General cosmetology service preparation, consultation, sanitation, client protection, service planning, completion, and professional follow-up. Current state requirements and manufacturer directions control where more specific.",
        "estimated_minutes": 120,
        "prerequisites": ["CrownPath professional conduct orientation"],
        "materials": ["Consenting model or mannequin", "Clean cosmetology tools", "Client protection supplies", "Sanitation/disinfection supplies", "Consultation form", "Manufacturer directions for products used"],
        "objectives": [
            "Prepare a compliant and organized workstation.",
            "Conduct an effective client consultation.",
            "Observe visible hair/scalp characteristics without diagnosis.",
            "Select services and products within lawful scope.",
            "Complete safe service closeout, sanitation, and client-care instructions.",
        ],
        "lesson_sections": [
            {"title": "Professional preparation", "content": "Prepare a clean workstation, organize required tools, separate clean and used items, inspect equipment, and protect the client appropriately before service begins."},
            {"title": "Consultation", "content": "Confirm service goals, relevant history, sensitivities, prior reactions, maintenance expectations, and visible hair/scalp condition. Clarify what the service can reasonably accomplish and stay within professional scope."},
            {"title": "Visible observation and referral boundaries", "content": "Describe visible characteristics such as dryness, oiliness, breakage, flakes, buildup, texture, density, or irritation neutrally. Do not diagnose disease. Modify, postpone, or refer when a concern falls outside cosmetic scope."},
            {"title": "Service and product planning", "content": "Choose tools, techniques, and products based on consultation, visible condition, service goal, manufacturer directions, and lawful scope. Do not improvise chemical or regulated procedures."},
            {"title": "Client protection and comfort", "content": "Use required draping or barriers, monitor temperature and comfort, communicate before major service changes, and stop when an unexpected reaction or safety concern occurs."},
            {"title": "Closeout and sanitation", "content": "Review the result, provide general cosmetic maintenance guidance, document relevant service information, dispose of single-use items properly, process reusable tools, and reset the workstation."},
        ],
        "steps": [
            "Sanitize the station and assemble clean tools.",
            "Discuss goals, history, sensitivities, and visible hair/scalp condition.",
            "Select the service plan and products within scope of practice.",
            "Complete the service, sanitation, and client-care instructions.",
        ],
        "demonstration": {
            "title": "Complete cosmetology service setup and closeout",
            "instructions": [
                "Prepare a clean station and client protection.",
                "Conduct a structured consultation and visible cosmetic observation.",
                "Select an instructor-approved service plan and products.",
                "Demonstrate comfort checks and safe professional boundaries.",
                "Complete service closeout, sanitation, documentation, and reset.",
            ],
        },
        "guided_practice": [
            "Learners prepare a workstation using a sanitation checklist.",
            "Learners practice consultation and neutral visible observation language.",
            "Learners choose between proceed, modify, postpone, and refer scenarios.",
            "Learners complete a service-closeout and station-reset simulation.",
        ],
        "knowledge_check": [
            {"question": "Which statement stays within cosmetology scope?", "options": ["You have psoriasis", "I can see visible redness and flaking, so I recommend postponing and seeking appropriate evaluation", "This product will cure the condition", "The camera confirms a disease"], "answer_index": 1, "rationale": "Cosmetology learners may describe visible findings and make safe service decisions without diagnosis."},
            {"question": "What should control professional product use?", "options": ["Guesswork", "Manufacturer directions and applicable rules", "The strongest possible method", "A social-media comment"], "answer_index": 1, "rationale": "Manufacturer directions and applicable professional requirements control product use."},
        ],
        "practical_checkoff": ["Prepares clean workstation", "Conducts consultation", "Uses neutral observation language", "Selects service within scope", "Protects client and monitors comfort", "Completes sanitation and closeout"],
        "instructor_notes": ["Require learners to distinguish cosmetic observation from diagnosis.", "Verify current jurisdiction-specific rules before representing any activity as approved licensure credit."],
        "student_handout": {"title": "CrownPath Cosmetology Foundations", "sections": ["PREPARE: station, tools, sanitation and client protection.", "CONSULT: goals, history, sensitivities and visible condition.", "PLAN: lawful service, approved products and manufacturer directions.", "SERVE: comfort, communication and professional boundaries.", "FINISH: client guidance, documentation, sanitation and reset."]},
        "printable": {"enabled": True, "exclude_answer_key_for_learners": True},
        "safety_note": "Current state-board and manufacturer requirements take priority over general training guidance. CrownPath cosmetology education does not authorize medical diagnosis or treatment.",
    }
}


INSTRUCTOR_ONLY_KEYS = {
    "answer_index",
    "rationale",
    "instructor_notes",
    "answer_key",
    "instructor_answer_key",
    "correct_answer",
}


def _sanitize_for_learner(value):
    if isinstance(value, dict):
        return {
            key: _sanitize_for_learner(item)
            for key, item in value.items()
            if key not in INSTRUCTOR_ONLY_KEYS
        }
    if isinstance(value, list):
        return [_sanitize_for_learner(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_for_learner(item) for item in value)
    return value


def get_canonical_lesson_content(lesson_id: str):
    for getter in (
        get_advanced_lesson_content,
        get_beauty_lesson_content,
        get_wellness_lesson_content,
        get_experience_agent_lesson_content,
        get_cosmetology_core_lesson_content,
        get_barber_core_lesson_content,
        get_home_care_lesson_content,
    ):
        content = getter(lesson_id)
        if content is not None:
            return content
    return FOUNDATION_LESSON_CONTENT.get(lesson_id)


def get_lesson_content(lesson_id: str):
    """Return a learner-safe copy of lesson content.

    Canonical instructor metadata remains server-side and can be accessed through
    get_canonical_lesson_content by trusted instructor/owner workflows.
    """
    content = get_canonical_lesson_content(lesson_id)
    if content is None:
        return None
    return _sanitize_for_learner(deepcopy(content))
