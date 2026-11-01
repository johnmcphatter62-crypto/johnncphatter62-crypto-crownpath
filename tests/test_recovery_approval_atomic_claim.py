"""Disposable SQLite test for atomic, single-use recovery approval claims.

Not connected to CrownPath production recovery.
"""
from concurrent.futures import ThreadPoolExecutor
import sqlite3


def _database(path):
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE recovery_approvals (
            approval_id TEXT PRIMARY KEY,
            used INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0, 1))
        )""")
        db.execute("INSERT INTO recovery_approvals(approval_id) VALUES ('fictional-approval')")


def _claim(path, approval_id):
    with sqlite3.connect(path, timeout=10) as db:
        result = db.execute(
            "UPDATE recovery_approvals SET used=1 WHERE approval_id=? AND used=0",
            (approval_id,),
        )
        return result.rowcount == 1


def test_approval_can_be_claimed_once(tmp_path):
    path = tmp_path / "recovery.db"
    _database(path)
    assert _claim(path, "fictional-approval")
    assert not _claim(path, "fictional-approval")


def test_unknown_approval_cannot_be_claimed(tmp_path):
    path = tmp_path / "recovery.db"
    _database(path)
    assert not _claim(path, "unknown-approval")


def test_two_simultaneous_claims_have_exactly_one_winner(tmp_path):
    path = tmp_path / "recovery.db"
    _database(path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _claim(path, "fictional-approval"), range(2)))
    assert sorted(results) == [False, True]
