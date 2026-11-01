"""Synthetic recovery audit field allowlist tests.

Audit records intentionally exclude request bodies and authentication secrets.
"""
import pytest


ALLOWED = {"actor_id", "backup_id", "outcome", "reason_code"}


def safe_event(request):
    event = {key: request[key] for key in ALLOWED if key in request}
    if not {"actor_id", "backup_id", "outcome"}.issubset(event):
        raise ValueError("Missing required audit fields")
    if event["outcome"] not in {"success", "denied", "failed"}:
        raise ValueError("Unsupported audit outcome")
    return event


def test_safe_fields_are_preserved():
    event = safe_event({"actor_id": "fictional-owner", "backup_id": "sample",
                        "outcome": "denied", "reason_code": "missing-approval"})
    assert event == {"actor_id": "fictional-owner", "backup_id": "sample",
                     "outcome": "denied", "reason_code": "missing-approval"}


def test_password_and_token_fields_are_excluded():
    event = safe_event({"actor_id": "fictional-owner", "backup_id": "sample",
                        "outcome": "failed", "password": "fictional-password",
                        "recovery_token": "fictional-token", "api_key": "fictional-key"})
    assert set(event) <= ALLOWED
    assert "fictional-password" not in str(event)
    assert "fictional-token" not in str(event)
    assert "fictional-key" not in str(event)


def test_nested_request_payload_is_not_logged():
    event = safe_event({"actor_id": "fictional-owner", "backup_id": "sample",
                        "outcome": "success",
                        "request_body": {"secret": "fictional-secret"}})
    assert "request_body" not in event
    assert "fictional-secret" not in str(event)


def test_missing_required_audit_fields_rejected():
    with pytest.raises(ValueError, match="Missing required"):
        safe_event({"outcome": "success"})


def test_unknown_outcome_rejected():
    with pytest.raises(ValueError, match="Unsupported"):
        safe_event({"actor_id": "fictional-owner", "backup_id": "sample",
                    "outcome": "unknown"})
