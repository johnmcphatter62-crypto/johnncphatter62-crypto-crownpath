"""Synthetic tenant-scoped recovery audit read tests.

All users, schools, and records are fictional; no production data is read.
"""
import sqlite3

import pytest


def _setup(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE recovery_audit (
            id INTEGER PRIMARY KEY,
            school_id TEXT NOT NULL,
            outcome TEXT NOT NULL
        )""")
        db.executemany(
            "INSERT INTO recovery_audit(school_id, outcome) VALUES (?,?)",
            [("school-a", "success"), ("school-b", "denied"),
             ("school-a", "failed")],
        )


def _read(path, principal, requested_school=None):
    if not principal or not principal.get("authenticated") or not principal.get("active"):
        raise PermissionError("Authentication required")
    if principal.get("role") != "OWNER" or not principal.get("audit_read"):
        raise PermissionError("Audit read permission required")
    school = principal["school_id"]
    if requested_school is not None and requested_school != school:
        raise PermissionError("Cross-school audit access denied")
    with sqlite3.connect(path) as db:
        return db.execute(
            "SELECT school_id, outcome FROM recovery_audit WHERE school_id=? ORDER BY id",
            (school,),
        ).fetchall()


def _owner(school_id="school-a", **changes):
    principal = {"authenticated": True, "active": True,
                 "role": "OWNER", "audit_read": True, "school_id": school_id}
    principal.update(changes)
    return principal


def test_owner_sees_only_own_school(tmp_path):
    path = tmp_path / "schools.db"
    _setup(path)
    assert _read(path, _owner()) == [
        ("school-a", "success"), ("school-a", "failed")
    ]


def test_other_school_owner_sees_only_their_records(tmp_path):
    path = tmp_path / "schools.db"
    _setup(path)
    assert _read(path, _owner("school-b")) == [("school-b", "denied")]


def test_request_cannot_override_authenticated_school(tmp_path):
    path = tmp_path / "schools.db"
    _setup(path)
    with pytest.raises(PermissionError, match="Cross-school"):
        _read(path, _owner(), requested_school="school-b")


def test_learner_cannot_read_school_audit(tmp_path):
    path = tmp_path / "schools.db"
    _setup(path)
    with pytest.raises(PermissionError, match="Audit read"):
        _read(path, _owner(role="COSMETOLOGY_PRO"))


def test_inactive_owner_cannot_read_school_audit(tmp_path):
    path = tmp_path / "schools.db"
    _setup(path)
    with pytest.raises(PermissionError, match="Authentication"):
        _read(path, _owner(active=False))
