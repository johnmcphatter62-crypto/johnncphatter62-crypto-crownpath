LESSON_CONTENT = {
    "home-care-foundations": {
        "summary": "Build a safe, respectful foundation for providing non-medical home-care support.",
        "objectives": ["Recognize basic client-safety priorities.", "Protect privacy, dignity, and personal choice.", "Know when a concern should be reported or escalated."],
        "steps": ["Check the environment for obvious hazards before beginning a task.", "Explain what you are about to do and obtain the client's cooperation.", "Use clean hands and appropriate protective practices.", "Document or report concerns according to the organization’s procedures."],
        "safety_note": "CrownPath training does not replace emergency services, clinical judgment, or state-required professional credentials."
    },
    "home-care-sanitation": {
        "summary": "Use sanitation and infection-control habits that reduce avoidable exposure in the home-care environment.",
        "objectives": ["Identify common contamination routes.", "Use hand hygiene at the right times.", "Separate clean items from contaminated items."],
        "steps": ["Clean hands before and after client-contact tasks.", "Use gloves or other protection when the task requires it.", "Clean reusable work surfaces and equipment according to product directions.", "Dispose of contaminated materials safely."],
        "safety_note": "Follow current employer, public-health, and state requirements when they are more specific than this lesson."
    },
    "home-care-communication": {
        "summary": "Practice calm, professional communication with clients, families, and supervisors.",
        "objectives": ["Use respectful client-centered language.", "Confirm instructions rather than guessing.", "Report changes clearly and promptly."],
        "steps": ["Introduce yourself and explain the purpose of the interaction.", "Listen without interrupting and confirm what you heard.", "Keep private information limited to authorized people.", "Use factual language when documenting or reporting."],
        "safety_note": "Urgent safety concerns should be escalated through the appropriate emergency or supervisory process."
    },
    "home-care-documentation": {
        "summary": "Create clear, factual records of home-care activities and observations.",
        "objectives": ["Separate facts from opinions.", "Record services accurately and promptly.", "Protect confidential records."],
        "steps": ["Record the date, time, service, and relevant observation.", "Use neutral and specific language.", "Correct errors according to the approved recordkeeping process.", "Store records only in authorized systems or locations."],
        "safety_note": "Documentation requirements vary by employer, payer, and jurisdiction; official requirements control."
    },
    "barber-foundations": {
        "summary": "Establish professional barbering habits for consultation, sanitation, tool handling, and service preparation.",
        "objectives": ["Prepare a clean workstation.", "Match tools to the planned service.", "Use a structured client consultation."],
        "steps": ["Sanitize the station and prepare clean tools.", "Discuss the desired result and inspect visible hair/scalp condition.", "Choose guards, combs, brushes, and products appropriate to the service.", "Maintain tool control and client comfort throughout the service."],
        "safety_note": "Follow current state-board sanitation, scope-of-practice, and licensing rules."
    },
    "barber-hair-scalp": {
        "summary": "Understand basic hair and scalp structure so barbering decisions are made more safely and accurately.",
        "objectives": ["Identify the basic hair shaft and follicle structures.", "Recognize visible conditions that may require service modification.", "Avoid diagnosing medical scalp disorders."],
        "steps": ["Observe density, texture, growth direction, and visible scalp condition.", "Ask about sensitivities and prior reactions.", "Modify or postpone service when a visible condition raises safety concerns.", "Refer medical concerns to an appropriate licensed healthcare professional."],
        "safety_note": "Barbering education is not medical diagnosis or treatment."
    },
    "barber-cutting-grooming": {
        "summary": "Use controlled sectioning, cutting, fading, and grooming sequences to produce consistent results.",
        "objectives": ["Plan a cut before removing length.", "Use guides and blending zones consistently.", "Finish and inspect the service systematically."],
        "steps": ["Establish the shape, length, and first guide.", "Work methodically through sections or fade zones.", "Cross-check balance and blend transitions.", "Detail the perimeter and finish according to the consultation."],
        "safety_note": "Keep blades, clippers, and sharp tools maintained and use them only as intended."
    },
    "barber-consultation-safety": {
        "summary": "Combine client consultation with shop-safety routines before, during, and after barber services.",
        "objectives": ["Confirm service expectations.", "Identify contraindications within barbering scope.", "Complete safe cleanup and reset."],
        "steps": ["Confirm desired style and relevant service history.", "Check tools, cords, surfaces, and client protection.", "Monitor comfort and stop if an unexpected reaction occurs.", "Clean, disinfect, store tools, and reset the workstation."],
        "safety_note": "Use the product label, manufacturer instructions, and applicable state-board rules as controlling guidance."
    },
    "cosmetology-foundations": {
        "summary": "Build a professional cosmetology service from consultation through sanitation and service completion.",
        "objectives": ["Prepare a compliant workstation.", "Conduct an effective consultation.", "Use safe service sequencing."],
        "steps": ["Sanitize the station and assemble clean tools.", "Discuss goals, history, sensitivities, and visible hair/scalp condition.", "Select the service plan and products within scope of practice.", "Complete the service, sanitation, and client-care instructions."],
        "safety_note": "Current state-board and manufacturer requirements take priority over general training guidance."
    },
    "cosmetology-hair-scalp": {
        "summary": "Connect hair-and-scalp science to cosmetology service selection and client safety.",
        "objectives": ["Identify basic hair and scalp structures.", "Recognize service-relevant differences in texture, porosity, and condition.", "Know when not to proceed with a cosmetic service."],
        "steps": ["Observe the hair and scalp under good lighting.", "Ask about prior services, sensitivities, and product reactions.", "Choose techniques based on condition and service goals.", "Refer suspected medical conditions rather than diagnosing them."],
        "safety_note": "This lesson is educational and does not authorize medical diagnosis or treatment."
    },
    "cosmetology-chemical-safety": {
        "summary": "Use a disciplined safety process for chemical-service preparation, product handling, and client monitoring.",
        "objectives": ["Follow product directions and warnings.", "Use required preliminary tests when applicable.", "Recognize when a chemical service should be stopped."],
        "steps": ["Read the full manufacturer instructions before mixing or applying.", "Perform required consultation and preliminary testing.", "Use ventilation, protection, timing, and application controls.", "Stop, rinse, or escalate according to instructions if an adverse reaction occurs."],
        "safety_note": "Never improvise chemical mixtures or exceed manufacturer directions."
    },
    "cosmetology-hair-replacement": {
        "summary": "Introduce non-surgical hair-replacement and scalp-application fundamentals within cosmetology education.",
        "objectives": ["Distinguish cosmetic hair replacement from surgical hair transplantation.", "Understand basic attachment and scalp-preparation concepts.", "Recognize when specialized medical or licensed services are required."],
        "steps": ["Consult on goals, scalp condition, sensitivities, and the type of hair-replacement system.", "Clean and prepare the scalp and system according to product directions.", "Use only cosmetic attachment methods that are lawful within the practitioner’s scope.", "Explain maintenance, removal, sanitation, and follow-up care."],
        "safety_note": "CrownPath does not teach or authorize surgical implantation, skin incision, graft harvesting, anesthesia, or other medical procedures."
    },
}


def get_lesson_content(lesson_id: str):
    return LESSON_CONTENT.get(lesson_id)
