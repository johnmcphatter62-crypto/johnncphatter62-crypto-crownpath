"""Synthetic recovery audit bounded time-window filtering tests."""
from datetime import datetime, timedelta, timezone
import sqlite3

import pytest


MAX_DAYS = 31


def _setup(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE recovery_audit (
            id INTEGER PRIMARY KEY, school_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL, outcome TEXT NOT NULL
        )""")
        db.executemany(
            "INSERT INTO recovery_audit(school_id, occurred_at, outcome) VALUES (?,?,?)",
            [("school-a", "2026-10-01T00:00:00+00:00", "success"),
             ("school-a", "2026-10-15T00:00:00+00:00", "failed"),
             ("school-a", "2026-11-01T00:00:00+00:00", "denied"),
             ("school-b", "2026-10-15T00:00:00+00:00", "success")],
        )


def _read(path, school, start, end):
    if not school:
        raise PermissionError("School context required")
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        raise ValueError("Datetime filters required")
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Timezone-aware filters required")
    start = start.astimezone(timezone.utc)
    end = end.astimezone(timezone.utc)
    if end <= start or end - start > timedelta(days=MAX_DAYS):
        raise ValueError("Invalid audit time window")
    with sqlite3.connect(path) as db:
        return db.execute(
            "SELECT outcome FROM recovery_audit WHERE school_id=? "
            "AND occurred_at>=? AND occurred_at<? ORDER BY id",
            (school, start.isoformat(timespec="seconds"),
             end.isoformat(timespec="seconds")),
        ).fetchall()


def _utc(day):
    return datetime(2026, 10, day, tzinfo=timezone.utc)


def test_bounded_window_and_school_scope(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    assert _read(path, "school-a", _utc(1), _utc(20)) == [
        ("success",), ("failed",)
    ]


def test_end_boundary_is_exclusive(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    assert _read(path, "school-a", _utc(1), _utc(15)) == [("success",)]


def test_overlong_window_rejected(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    with pytest.raises(ValueError, match="time window"):
        _read(path, "school-a", _utc(1), _utc(1) + timedelta(days=32))


def test_reversed_and_empty_windows_rejected(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    for start, end in [(_utc(15), _utc(1)), (_utc(1), _utc(1))]:
        with pytest.raises(ValueError, match="time window"):
            _read(path, "school-a", start, end)


def test_naive_timestamps_rejected(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    with pytest.raises(ValueError, match="Timezone-aware"):
        _read(path, "school-a", datetime(2026, 10, 1), _utc(15))
