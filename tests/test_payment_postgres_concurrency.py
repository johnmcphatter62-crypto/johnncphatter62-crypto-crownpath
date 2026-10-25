"""Concurrent synthetic payment delivery against explicitly disposable local PostgreSQL.

This test does not import CrownPath application code or touch payment providers.
"""
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlsplit

url = os.environ.get("CROWNPATH_TEST_POSTGRES_URL", "")
parts = urlsplit(url)
if (
    parts.scheme not in ("postgresql", "postgresql+psycopg")
    or parts.hostname not in ("localhost", "127.0.0.1", "::1")
    or "disposable" not in parts.path.lower()
    or os.environ.get("CROWNPATH_DATABASE_URL") != url
    or os.environ.get("CROWNPATH_ENV") != "staging"
    or os.environ.get("CROWNPATH_TEST_DB_DISPOSABLE") != "YES"
):
    raise unittest.SkipTest("Only explicitly configured local disposable PostgreSQL permitted")

import psycopg


class SyntheticPostgresPaymentConcurrencyTest(unittest.TestCase):
    def test_simultaneous_duplicate_event_one_entitlement(self):
        dsn = url.replace("postgresql+psycopg://", "postgresql://", 1)
        with psycopg.connect(dsn, autocommit=True) as db:
            db.execute("CREATE TEMP TABLE unused_guard (id integer)")
            db.execute("CREATE TABLE IF NOT EXISTS synthetic_payment_race_orders (order_id text PRIMARY KEY, status text NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS synthetic_payment_race_events (provider text NOT NULL, event_id text NOT NULL, order_id text NOT NULL, PRIMARY KEY(provider,event_id))")
            db.execute("CREATE TABLE IF NOT EXISTS synthetic_payment_race_entitlements (order_id text PRIMARY KEY)")
            db.execute("DELETE FROM synthetic_payment_race_entitlements")
            db.execute("DELETE FROM synthetic_payment_race_events")
            db.execute("DELETE FROM synthetic_payment_race_orders")
            db.execute("INSERT INTO synthetic_payment_race_orders VALUES ('synthetic-race-order','PENDING')")
        barrier = Barrier(2)

        def deliver():
            with psycopg.connect(dsn) as conn:
                barrier.wait(timeout=15)
                with conn.transaction():
                    row = conn.execute(
                        "SELECT status FROM synthetic_payment_race_orders WHERE order_id=%s FOR UPDATE",
                        ("synthetic-race-order",),
                    ).fetchone()
                    if row[0] == "PAID":
                        return "duplicate"
                    conn.execute(
                        "INSERT INTO synthetic_payment_race_events VALUES (%s,%s,%s)",
                        ("synthetic-provider", "synthetic-event", "synthetic-race-order"),
                    )
                    conn.execute(
                        "UPDATE synthetic_payment_race_orders SET status='PAID' WHERE order_id=%s",
                        ("synthetic-race-order",),
                    )
                    conn.execute(
                        "INSERT INTO synthetic_payment_race_entitlements VALUES (%s)",
                        ("synthetic-race-order",),
                    )
                    return "applied"

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(deliver)
                b = pool.submit(deliver)
                self.assertEqual(sorted([a.result(timeout=30), b.result(timeout=30)]), ["applied", "duplicate"])
            with psycopg.connect(dsn) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM synthetic_payment_race_events").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM synthetic_payment_race_entitlements").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT status FROM synthetic_payment_race_orders").fetchone()[0], "PAID")
        finally:
            with psycopg.connect(dsn, autocommit=True) as db:
                db.execute("DROP TABLE IF EXISTS synthetic_payment_race_entitlements")
                db.execute("DROP TABLE IF EXISTS synthetic_payment_race_events")
                db.execute("DROP TABLE IF EXISTS synthetic_payment_race_orders")


if __name__ == "__main__":
    unittest.main()
