"""Synthetic cross-school backup validation. No live data."""
import hashlib
import hmac

import pytest

KEY = b"test-key-only"


def make_record(data, school):
    digest = hashlib.sha256(data).hexdigest()
    proof = hmac.new(KEY, (school + ":" + digest).encode(), hashlib.sha256).hexdigest()
    return {"school": school, "digest": digest, "proof": proof}


def validate(data, record, expected_school):
    signed = (record["school"] + ":" + record["digest"]).encode()
    proof = hmac.new(KEY, signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(proof, record["proof"]):
        raise ValueError("signature")
    if not hmac.compare_digest(hashlib.sha256(data).hexdigest(), record["digest"]):
        raise ValueError("content")
    if record["school"] != expected_school:
        raise ValueError("school")
    return True


def test_matching_school():
    data = b"sample"
    assert validate(data, make_record(data, "school-a"), "school-a")


def test_other_school_denied():
    data = b"sample"
    with pytest.raises(ValueError, match="school"):
        validate(data, make_record(data, "school-a"), "school-b")


def test_changed_school_label_denied():
    data = b"sample"
    record = make_record(data, "school-a")
    record["school"] = "school-b"
    with pytest.raises(ValueError, match="signature"):
        validate(data, record, "school-b")


def test_changed_content_denied():
    data = b"sample"
    with pytest.raises(ValueError, match="content"):
        validate(b"modified", make_record(data, "school-a"), "school-a")
