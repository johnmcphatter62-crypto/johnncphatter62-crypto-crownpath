"""Synthetic transaction tests; uses only an in-memory disposable SQLite database."""
import sqlite3
import unittest
from tests.synthetic_payment_ledger_helper import initialize, process_paid_event


class SyntheticPaymentLedgerTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:",isolation_level=None)
        initialize(self.db)
        self.db.execute("INSERT INTO synthetic_orders VALUES('test-order','PENDING')")

    def tearDown(self):
        self.db.close()

    def pay(self, event="event-1", verified=True, order="test-order"):
        return process_paid_event(self.db,"test-provider",event,order,"test-learner",verified)

    def test_paid_once_duplicate_event_no_second_entitlement(self):
        self.assertTrue(self.pay())
        self.assertFalse(self.pay())
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_entitlements").fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_events").fetchone()[0],1)

    def test_distinct_second_event_rejected(self):
        self.pay()
        with self.assertRaises(ValueError):
            self.pay("event-2")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_events").fetchone()[0],1)

    def test_invalid_event_does_not_change_order(self):
        with self.assertRaises(ValueError):
            self.pay(verified=False)
        self.assertEqual(self.db.execute("SELECT status FROM synthetic_orders").fetchone()[0],"PENDING")

    def test_missing_order_rolls_back(self):
        with self.assertRaises(ValueError):
            self.pay(order="missing")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_events").fetchone()[0],0)

    def test_entitlement_insert_failure_rolls_back_state_and_event(self):
        self.db.execute("INSERT INTO synthetic_entitlements VALUES('test-order','existing')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.pay()
        self.assertEqual(self.db.execute("SELECT status FROM synthetic_orders").fetchone()[0],"PENDING")
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM synthetic_events").fetchone()[0],0)


if __name__=="__main__":
    unittest.main()
