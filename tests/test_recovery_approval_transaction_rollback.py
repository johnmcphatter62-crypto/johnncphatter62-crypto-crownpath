"""Synthetic atomic approval and recovery-action transaction tests.

Uses disposable SQLite only; no production restore or real authorization.
"""
import sqlite3

import pytest


def _setup(path):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE approvals (id TEXT PRIMARY KEY, used INTEGER NOT NULL DEFAULT 0)")
        db.execute("CREATE TABLE restore_events (approval_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
        db.execute("INSERT INTO approvals(id) VALUES ('sample-approval')")


def _recover(path, approval_id, fail=False):
    with sqlite3.connect(path) as db:
        changed = db.execute(
            "UPDATE approvals SET used=1 WHERE id=? AND used=0", (approval_id,)
        ).rowcount
        if changed != 1:
            raise PermissionError("Approval unavailable")
        if fail:
            raise RuntimeError("Synthetic restore failed")
        db.execute(
            "INSERT INTO restore_events(approval_id, status) VALUES (?, 'simulated')",
            (approval_id,),
        )


def _state(path):
    with sqlite3.connect(path) as db:
        used = db.execute("SELECT used FROM approvals WHERE id='sample-approval'").fetchone()[0]
        events = db.execute("SELECT COUNT(*) FROM restore_events").fetchone()[0]
        return used, events


def test_success_commits_approval_and_simulated_event(tmp_path):
    path = tmp_path / "test.db"
    _setup(path)
    _recover(path, "sample-approval")
    assert _state(path) == (1, 1)


def test_failure_rolls_back_approval_and_event(tmp_path):
    path = tmp_path / "test.db"
    _setup(path)
    with pytest.raises(RuntimeError, match="failed"):
        _recover(path, "sample-approval", fail=True)
    assert _state(path) == (0, 0)


def test_failed_attempt_can_be_retried(tmp_path):
    path = tmp_path / "test.db"
    _setup(path)
    with pytest.raises(RuntimeError):
        _recover(path, "sample-approval", fail=True)
    _recover(path, "sample-approval")
    assert _state(path) == (1, 1)


def test_committed_approval_cannot_be_reused(tmp_path):
    path = tmp_path / "test.db"
    _setup(path)
    _recover(path, "sample-approval")
    with pytest.raises(PermissionError, match="unavailable"):
        _recover(path, "sample-approval")
    assert _state(path) == (1, 1)
