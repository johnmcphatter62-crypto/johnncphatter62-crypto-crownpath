"""Validation policy for CrownPath instructor assessment evidence.

This module does not store files, access medical records, or approve credentials.
References are opaque identifiers issued by a trusted evidence store.
"""
from dataclasses import dataclass
from typing import Mapping


ALLOWED_EVIDENCE_TYPES = frozenset({"OBSERVATION_NOTE", "PHOTO", "VIDEO", "DOCUMENT"})


@dataclass(frozen=True)
class EvidenceValidation:
    valid: bool
    errors: tuple[str, ...]


def validate_assessment_evidence(
    evidence: Mapping[str, object],
    *,
    require_consent: bool = False,
) -> EvidenceValidation:
    errors: list[str] = []
    if not isinstance(evidence, Mapping):
        return EvidenceValidation(False, ("Evidence must be a mapping.",))
    evidence_type = evidence.get("type")
    if evidence_type not in ALLOWED_EVIDENCE_TYPES:
        errors.append("Unsupported evidence type.")
    reference = evidence.get("reference")
    if not isinstance(reference, str) or not reference.strip() or len(reference) > 200:
        errors.append("A valid evidence reference is required.")
    elif any(ord(char) < 32 for char in reference):
        errors.append("Evidence reference contains control characters.")
    note = evidence.get("observation_note")
    if not isinstance(note, str) or not note.strip() or len(note) > 4000:
        errors.append("An observation note of 1–4000 characters is required.")
    if require_consent and evidence.get("consent_confirmed") is not True:
        errors.append("Explicit consent confirmation is required.")
    return EvidenceValidation(not errors, tuple(errors))
