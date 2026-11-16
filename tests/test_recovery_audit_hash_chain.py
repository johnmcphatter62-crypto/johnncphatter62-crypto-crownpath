"""Synthetic hash-linked recovery audit verification.

A hash chain detects edits when its trusted final digest is kept separately.
This test is not immutable production audit storage.
"""
import hashlib
import json

import pytest


def _digest(previous, event):
    data = json.dumps({"previous": previous, "event": event},
                      sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(data).hexdigest()


def _append(chain, event):
    previous = chain[-1]["digest"] if chain else "GENESIS"
    chain.append({"previous": previous, "event": dict(event),
                  "digest": _digest(previous, event)})


def _verify(chain, trusted_tip):
    previous = "GENESIS"
    for entry in chain:
        if entry["previous"] != previous:
            raise ValueError("Broken audit chain")
        if entry["digest"] != _digest(previous, entry["event"]):
            raise ValueError("Modified audit record")
        previous = entry["digest"]
    if previous != trusted_tip:
        raise ValueError("Audit history truncated or replaced")
    return True


def _chain():
    chain = []
    _append(chain, {"backup": "fictional-a", "outcome": "denied"})
    _append(chain, {"backup": "fictional-a", "outcome": "success"})
    return chain


def test_intact_audit_history_passes():
    chain = _chain()
    assert _verify(chain, chain[-1]["digest"])


def test_modified_earlier_outcome_is_detected():
    chain = _chain()
    trusted_tip = chain[-1]["digest"]
    chain[0]["event"]["outcome"] = "success"
    with pytest.raises(ValueError, match="Modified"):
        _verify(chain, trusted_tip)


def test_deleted_earlier_record_is_detected():
    chain = _chain()
    trusted_tip = chain[-1]["digest"]
    chain.pop(0)
    with pytest.raises(ValueError, match="Broken"):
        _verify(chain, trusted_tip)


def test_truncated_history_is_detected_using_external_tip():
    chain = _chain()
    trusted_tip = chain[-1]["digest"]
    chain.pop()
    with pytest.raises(ValueError, match="truncated"):
        _verify(chain, trusted_tip)
