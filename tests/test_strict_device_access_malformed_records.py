"""Fail-closed malformed device tests using disposable database state."""
import pytest
import sqlalchemy as sa

from crownpath.strict_device_access import strict_authorized_visible_devices


@pytest.fixture
def db():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE TABLE users (user_id TEXT PRIMARY KEY, role TEXT NOT NULL, active BOOLEAN NOT NULL)"
        ))
        conn.execute(sa.text(
            "CREATE TABLE schools (school_id TEXT PRIMARY KEY, active BOOLEAN NOT NULL)"
        ))
        conn.execute(sa.text(
            "CREATE TABLE school_memberships (membership_id TEXT PRIMARY KEY, "
            "school_id TEXT NOT NULL, user_id TEXT NOT NULL, active BOOLEAN NOT NULL, "
            "approved_by_user_id TEXT, approved_at TEXT, revoked_at TEXT)"
        ))
        conn.execute(sa.text(
            "INSERT INTO users VALUES ('learner', 'COSMETOLOGY_PRO', TRUE), "
            "('owner', 'OWNER', TRUE)"
        ))
        conn.execute(sa.text("INSERT INTO schools VALUES ('school-a', TRUE)"))
        conn.execute(sa.text(
            "INSERT INTO school_memberships VALUES "
            "('membership', 'school-a', 'learner', TRUE, 'owner', '2026-11-04', NULL)"
        ))
        yield conn
    engine.dispose()


def record(**changes):
    item = {"id": "camera-1", "owner_id": "learner", "school_id": "school-a",
            "approved": True, "revoked": False, "transport": "wifi"}
    item.update(changes)
    return item


def visible(db, records):
    return strict_authorized_visible_devices(
        db, {"user_id": "learner", "active": True}, records
    )


@pytest.mark.parametrize("invalid", [
    None, [], "camera-1", {},
    record(id=""), record(id=None), record(id=42),
    record(owner_id="other"), record(owner_id=None),
    record(school_id="school-b"), record(school_id=None),
    record(approved=False), record(approved=1), record(approved=None),
    record(revoked=True), record(revoked=None),
    record(transport="usb"), record(transport="WIFI"),
    record(transport=None),
])
def test_malformed_device_not_visible(db, invalid):
    assert visible(db, [invalid]) == []


def test_malformed_records_do_not_hide_valid_records(db):
    assert visible(db, [None, record(id="valid"), {}, record(transport="usb")]) == [
        record(id="valid")
    ]


def test_bluetooth_and_wifi_are_supported_without_hardware_access(db):
    result = visible(db, [record(id="bluetooth", transport="bluetooth"),
                          record(id="wifi", transport="wifi")])
    assert [device["id"] for device in result] == ["bluetooth", "wifi"]
