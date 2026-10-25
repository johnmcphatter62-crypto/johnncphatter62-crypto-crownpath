"""Disposable SQLite payment-event exercise; no checkout or production access."""
import sqlite3

def initialize(connection):
    connection.executescript("""
CREATE TABLE IF NOT EXISTS synthetic_orders (order_id TEXT PRIMARY KEY, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS synthetic_events (provider TEXT NOT NULL, event_id TEXT NOT NULL, order_id TEXT NOT NULL, PRIMARY KEY(provider,event_id));
CREATE TABLE IF NOT EXISTS synthetic_entitlements (order_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL);
""")

def process_paid_event(connection, provider, event_id, order_id, learner_id, verified):
    """Fixture verification flag is not real webhook signature validation."""
    if not verified or not all((provider,event_id,order_id,learner_id)):
        raise ValueError("Invalid synthetic event")
    connection.execute("BEGIN IMMEDIATE")
    try:
        existing=connection.execute("SELECT order_id FROM synthetic_events WHERE provider=? AND event_id=?",(provider,event_id)).fetchone()
        if existing:
            if existing[0]!=order_id:
                raise ValueError("Conflicting duplicate")
            connection.commit()
            return False
        row=connection.execute("SELECT status FROM synthetic_orders WHERE order_id=?",(order_id,)).fetchone()
        if row is None or row[0]!="PENDING":
            raise ValueError("Order not pending")
        connection.execute("INSERT INTO synthetic_events VALUES(?,?,?)",(provider,event_id,order_id))
        connection.execute("UPDATE synthetic_orders SET status='PAID' WHERE order_id=?",(order_id,))
        connection.execute("INSERT INTO synthetic_entitlements VALUES(?,?)",(order_id,learner_id))
        connection.commit()
        return True
    except BaseException:
        connection.rollback()
        raise
