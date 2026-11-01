"""Synthetic disaster-recovery completeness gate for classroom snapshots.

Ensures an authenticated-looking snapshot cannot be accepted if required
curriculum or learner progress records are missing. No production access.
"""
import hashlib
import hmac
import json

import pytest


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _manifest(snapshot, key):
    raw = _canonical(snapshot)
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "signature": hmac.new(key, raw, hashlib.sha256).hexdigest()}


def _verify(snapshot, record, key, expected_lesson_ids, expected_progress_keys):
    raw = _canonical(snapshot)
    digest = hashlib.sha256(raw).hexdigest()
    signature = hmac.new(key, raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, record["sha256"]) or not hmac.compare_digest(
        signature, record["signature"]
    ):
        raise ValueError("Untrusted snapshot")
    lessons = {row["id"] for row in snapshot["lessons"]}
    progress = {(row["learner_id"], row["lesson_id"]) for row in snapshot["progress"]}
    if not expected_lesson_ids.issubset(lessons):
        raise ValueError("Missing required curriculum")
    if not expected_progress_keys.issubset(progress):
        raise ValueError("Missing required learner progress")
    if any(row["lesson_id"] not in lessons for row in snapshot["progress"]):
        raise ValueError("Orphaned learner progress")
    return True


def _snapshot():
    return {"lessons": [{"id": "fictional-lesson-1"}, {"id": "fictional-lesson-2"}],
            "progress": [{"learner_id": "fictional-learner", "lesson_id": "fictional-lesson-1"}]}


def _check(snapshot, record):
    return _verify(snapshot, record, b"synthetic-only-key",
                   {"fictional-lesson-1", "fictional-lesson-2"},
                   {("fictional-learner", "fictional-lesson-1")})


def test_complete_snapshot_is_eligible():
    snapshot = _snapshot()
    assert _check(snapshot, _manifest(snapshot, b"synthetic-only-key"))


def test_signed_but_incomplete_curriculum_is_rejected():
    snapshot = _snapshot()
    snapshot["lessons"].pop()
    with pytest.raises(ValueError, match="Missing required curriculum"):
        _check(snapshot, _manifest(snapshot, b"synthetic-only-key"))


def test_signed_but_missing_progress_is_rejected():
    snapshot = _snapshot()
    snapshot["progress"].clear()
    with pytest.raises(ValueError, match="Missing required learner progress"):
        _check(snapshot, _manifest(snapshot, b"synthetic-only-key"))


def test_signed_orphaned_progress_is_rejected():
    snapshot = _snapshot()
    snapshot["progress"].append({"learner_id": "fictional-learner",
                                 "lesson_id": "missing-lesson"})
    with pytest.raises(ValueError, match="Orphaned learner progress"):
        _check(snapshot, _manifest(snapshot, b"synthetic-only-key"))


def test_unsigned_snapshot_mutation_is_rejected():
    snapshot = _snapshot()
    record = _manifest(snapshot, b"synthetic-only-key")
    snapshot["lessons"].pop()
    with pytest.raises(ValueError, match="Untrusted snapshot"):
        _check(snapshot, record)
