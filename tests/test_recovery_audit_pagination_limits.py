"""Synthetic recovery audit pagination and tenant scoping tests.

All data is fictional and stored in disposable SQLite.
"""
import sqlite3

import pytest


MAX_PAGE_SIZE = 50


def _setup(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE recovery_audit (
            id INTEGER PRIMARY KEY, school_id TEXT NOT NULL, outcome TEXT NOT NULL
        )""")
        db.executemany(
            "INSERT INTO recovery_audit(school_id, outcome) VALUES (?, ?)",
            [("school-a" if i % 2 == 0 else "school-b", "success")
             for i in range(130)],
        )


def _page(path, authenticated_school, limit=20, offset=0):
    if not authenticated_school:
        raise PermissionError("Authenticated school required")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_PAGE_SIZE:
        raise ValueError("Invalid audit page size")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("Invalid audit offset")
    with sqlite3.connect(path) as db:
        return db.execute(
            "SELECT id, school_id, outcome FROM recovery_audit "
            "WHERE school_id=? ORDER BY id LIMIT ? OFFSET ?",
            (authenticated_school, limit, offset),
        ).fetchall()


def test_default_page_is_bounded(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    assert len(_page(path, "school-a")) == 20


def test_maximum_page_size_is_enforced(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    assert len(_page(path, "school-a", limit=50)) == 50
    with pytest.raises(ValueError, match="page size"):
        _page(path, "school-a", limit=51)


@pytest.mark.parametrize("limit", [0, -1, 1.5, True])
def test_invalid_page_sizes_rejected(tmp_path, limit):
    path = tmp_path / "audit.db"
    _setup(path)
    with pytest.raises(ValueError, match="page size"):
        _page(path, "school-a", limit=limit)


@pytest.mark.parametrize("offset", [-1, 1.5, True])
def test_invalid_offsets_rejected(tmp_path, offset):
    path = tmp_path / "audit.db"
    _setup(path)
    with pytest.raises(ValueError, match="offset"):
        _page(path, "school-a", offset=offset)


def test_pages_do_not_overlap_and_remain_school_scoped(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    first = _page(path, "school-a", limit=20, offset=0)
    second = _page(path, "school-a", limit=20, offset=20)
    assert set(row[0] for row in first).isdisjoint(row[0] for row in second)
    assert all(row[1] == "school-a" for row in first + second)


def test_missing_school_context_denied(tmp_path):
    path = tmp_path / "audit.db"
    _setup(path)
    with pytest.raises(PermissionError, match="Authenticated"):
        _page(path, None)
