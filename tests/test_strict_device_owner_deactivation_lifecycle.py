"""Disposable DB lifecycle test for Owner deactivation and reactivation.

No live routes, devices, or production credentials are used.
"""
import sqlalchemy as sa

from crownpath.strict_device_access import strict_authorized_visible_devices


def test_owner_deactivation_revokes_visibility_until_new_valid_approval():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.begin() as db:
            db.execute(sa.text(
                "CREATE TABLE users (user_id TEXT PRIMARY KEY, role TEXT NOT NULL, active BOOLEAN NOT NULL)"
            ))
            db.execute(sa.text(
                "CREATE TABLE schools (school_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"
            ))
            db.execute(sa.text(
                "CREATE TABLE school_memberships (membership_id TEXT PRIMARY KEY, "
                "school_id TEXT NOT NULL, user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
                "approved_by_user_id TEXT, approved_at TEXT, revoked_at TEXT)"
            ))
            db.execute(sa.text(
                "INSERT INTO users VALUES ('learner', 'COSMETOLOGY_PRO', TRUE), "
                "('owner', 'OWNER', TRUE), ('other-owner', 'OWNER', TRUE)"
            ))
            db.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
            db.execute(sa.text(
                "INSERT INTO school_memberships VALUES "
                "('membership', 'school-a', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
            ))

            principal = {"user_id": "learner", "active": True}
            devices = [{"id": "wifi-1", "owner_id": "learner", "school_id": "school-a",
                        "approved": True, "revoked": False, "transport": "wifi"}]

            def visible():
                return strict_authorized_visible_devices(db, principal, devices)

            assert [d["id"] for d in visible()] == ["wifi-1"]

            db.execute(sa.text("UPDATE users SET active = FALSE WHERE user_id = 'owner'"))
            assert visible() == []

            # Another active Owner must be explicitly recorded as approver.
            db.execute(sa.text(
                "UPDATE school_memberships SET approved_by_user_id = 'other-owner' "
                "WHERE membership_id = 'membership'"
            ))
            assert [d["id"] for d in visible()] == ["wifi-1"]

            db.execute(sa.text(
                "UPDATE users SET role = 'INSTRUCTOR' WHERE user_id = 'other-owner'"
            ))
            assert visible() == []
    finally:
        engine.dispose()
