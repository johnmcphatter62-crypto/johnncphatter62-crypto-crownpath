"""Regression checks for the first-Owner transaction."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from crownpath import auth
from crownpath.models import User


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'owner-activation.db'}")
    User.__table__.create(engine)
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(auth, "session", factory)
    try:
        yield factory
    finally:
        engine.dispose()


def test_existing_account_keeps_role_and_password(sessions, monkeypatch):
    email = "existing@example.com"
    monkeypatch.setenv("CROWNPATH_OWNER_EMAIL", email)
    monkeypatch.setenv("CROWNPATH_OWNER_ACTIVATION_CODE", "synthetic-code")
    with sessions.begin() as db:
        db.add(User(user_id="existing", name="Existing", email=email,
                    password_hash="original-hash", role="BARBER"))

    with pytest.raises(ValueError, match="Existing account requires"):
        auth.create_owner("Replacement", email, "synthetic-password", "synthetic-code")

    with sessions() as db:
        account = db.get(User, "existing")
        assert (account.name, account.role, account.password_hash) == (
            "Existing", "BARBER", "original-hash",
        )


def test_concurrent_bootstrap_with_distinct_emails_creates_one_owner(sessions, monkeypatch):
    config = local()
    start = Barrier(2)
    monkeypatch.setattr(auth, "os", SimpleNamespace(
        getenv=lambda key, default="": config.values.get(key, default),
    ))

    def activate(email):
        config.values = {
            "CROWNPATH_OWNER_EMAIL": email,
            "CROWNPATH_OWNER_ACTIVATION_CODE": "synthetic-code",
        }
        start.wait(timeout=10)
        try:
            return auth.create_owner("Owner", email, "synthetic-password", "synthetic-code")["email"]
        except ValueError as exc:
            assert str(exc) == "Owner activation is already complete."
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(activate, ("one@example.com", "two@example.com")))
    winners = [email for email in results if email is not None]
    assert len(winners) == 1
    with sessions() as db:
        assert list(db.scalars(select(User.email).where(User.role == "OWNER"))) == winners
