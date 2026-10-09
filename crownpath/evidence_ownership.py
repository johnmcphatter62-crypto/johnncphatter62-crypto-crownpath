"""Trusted evidence ownership policy for future assessment submission.

No database or remote storage is queried here. The caller must supply
a server-verified reference-to-learner mapping, never client-provided ownership.
"""
from collections.abc import Mapping


def validate_evidence_ownership(
    learner_id: str,
    evidence_refs: list[str],
    trusted_owner_by_reference: Mapping[str, str],
) -> bool:
    if not isinstance(learner_id, str) or not learner_id.strip():
        return False
    if not isinstance(evidence_refs, list) or not evidence_refs:
        return False
    if len(set(evidence_refs)) != len(evidence_refs):
        return False
    for ref in evidence_refs:
        if not isinstance(ref, str) or not ref.strip():
            return False
        if trusted_owner_by_reference.get(ref) != learner_id:
            return False
    return True
