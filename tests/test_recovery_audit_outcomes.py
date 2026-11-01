"""Disposable recovery audit trail policy tests.

Audit events are fictional and contain no credentials or live user data.
"""
import sqlite3

import pytest


def _initialize(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE audit_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor TEXT NOT NULL,
            backup_id TEXT NOT NULL,
            outcome TEXT NOT NULL CHECK(outcome IN ('success','denied','failed')),
            reason TEXT NOT NULL
        )""")


def _record(path, actor, backup_id, outcome, reason):
    if outcome not in {"success", "denied", "failed"}:
        raise ValueError("Unsupported recovery outcome")
    with sqlite3.connect(path) as db:
        db.execute(
            "INSERT INTO audit_events(actor, backup_id, outcome, reason) VALUES (?,?,?,?)",
            (actor, backup_id, outcome, reason),
        )


def _events(path):
    with sqlite3.connect(path) as db:
        return db.execute(
            "SELECT actor, backup_id, outcome, reason FROM audit_events ORDER BY event_id"
        ).fetchall()


@pytest.mark.parametrize("outcome,reason", [
    ("success", "simulated-restore-complete"),
    ("denied", "owner-authorization-required"),
    ("failed", "synthetic-integrity-error"),
])
def test_each_recovery_outcome_is_recorded(tmp_path, outcome, reason):
    path = tmp_path / "audit.db"
    _initialize(path)
    _record(path, "fictional-owner", "fictional-backup", outcome, reason)
    assert _events(path) == [
        ("fictional-owner", "fictional-backup", outcome, reason)
    ]


def test_multiple_attempts_remain_distinct_and_ordered(tmp_path):
    path = tmp_path / "audit.db"
    _initialize(path)
    _record(path, "fictional-owner", "backup-a", "denied", "missing-approval")
    _record(path, "fictional-owner", "backup-a", "success", "approved-retry")
    assert [event[2] for event in _events(path)] == ["denied", "success"]


def test_invalid_outcome_is_not_written(tmp_path):
    path = tmp_path / "audit.db"
    _initialize(path)
    with pytest.raises(ValueError, match="Unsupported"):
        _record(path, "fictional-owner", "backup-a", "unknown", "test")
    assert _events(path) == []
