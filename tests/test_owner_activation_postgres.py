"""Verify first-Owner activation against disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from crownpath import auth
from crownpath.models import User
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


def test_only_one_first_owner_is_created_across_distinct_configured_emails(
    isolated_logout_engine, monkeypatch,
):
    sessions = sessionmaker(bind=isolated_logout_engine)
    config = local()
    start = Barrier(2)
    monkeypatch.setattr(auth, "session", sessions)
    monkeypatch.setattr(auth, "os", SimpleNamespace(
        getenv=lambda name, default="": config.values.get(name, default),
    ))

    def activate(email):
        config.values = {
            "CROWNPATH_OWNER_EMAIL": email,
            "CROWNPATH_OWNER_ACTIVATION_CODE": "synthetic-activation-code",
        }
        start.wait(timeout=10)
        try:
            result = auth.create_owner("Test Owner", email, "Synthetic-password-01", config.values[
                "CROWNPATH_OWNER_ACTIVATION_CODE"
            ])
            return "created", result["email"]
        except ValueError as error:
            return "rejected", str(error)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(activate, ["one@example.com", "two@example.com"]))
    created = [email for status, email in results if status == "created"]
    assert len(created) == 1
    assert ("rejected", "Owner activation is already complete.") in results
    with sessions() as db:
        assert list(db.scalars(select(User.email).where(User.role == "OWNER"))) == created
