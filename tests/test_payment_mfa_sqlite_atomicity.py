"""Disposable SQLite atomic one-time proof consumption tests.

Exercises database uniqueness and atomic UPDATE under concurrency.
This is NOT a production proof service or a PostgreSQL integration test.
"""
import os
import sqlite3
import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

def _connect(path):
    db = sqlite3.connect(path, timeout=10)
    db.execute("PRAGMA busy_timeout=10000")
    return db

def test_atomic_single_use_across_independent_connections():
    with tempfile.TemporaryDirectory(prefix="crownpath-mfa-") as directory:
        path = os.path.join(directory, "proofs.sqlite3")
        with _connect(path) as db:
            db.execute("CREATE TABLE proofs (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, purpose TEXT NOT NULL, expires_at INTEGER NOT NULL, used_at INTEGER)")
            db.execute("INSERT INTO proofs VALUES (?, ?, ?, ?, NULL)", ("synthetic-hash", "owner-1", "payments.configure", 500))
        barrier = Barrier(8)

        def consume(_):
            barrier.wait(timeout=10)
            with _connect(path) as db:
                result = db.execute(
                    "UPDATE proofs SET used_at=? WHERE token_hash=? AND user_id=? AND purpose=? AND used_at IS NULL AND expires_at>?",
                    (100, "synthetic-hash", "owner-1", "payments.configure", 100),
                )
                db.commit()
                return result.rowcount == 1

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(consume, range(8)))
        assert results.count(True) == 1
        assert results.count(False) == 7

def test_wrong_identity_or_expired_proof_denied():
    with tempfile.TemporaryDirectory(prefix="crownpath-mfa-") as directory:
        path = os.path.join(directory, "proofs.sqlite3")
        with _connect(path) as db:
            db.execute("CREATE TABLE proofs (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, purpose TEXT NOT NULL, expires_at INTEGER NOT NULL, used_at INTEGER)")
            db.execute("INSERT INTO proofs VALUES ('test-hash', 'owner-1', 'payments.configure', 99, NULL)")
            for user in ("owner-1", "other-user"):
                result = db.execute("UPDATE proofs SET used_at=100 WHERE token_hash='test-hash' AND user_id=? AND purpose='payments.configure' AND used_at IS NULL AND expires_at>100", (user,))
                assert result.rowcount == 0
