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


def test_concurrent_http_activation_issues_only_one_session(isolated_logout_engine, monkeypatch):
    from fastapi.testclient import TestClient

    from crownpath.main import app
    from crownpath.models import AuthToken

    sessions = sessionmaker(bind=isolated_logout_engine)
    monkeypatch.setattr(auth, "session", sessions)
    monkeypatch.setenv("CROWNPATH_OWNER_EMAIL", "first-owner@example.com")
    monkeypatch.setenv("CROWNPATH_OWNER_ACTIVATION_CODE", "synthetic-activation-code")
    start = Barrier(2)

    def activate():
        with TestClient(app, headers={"Origin": "http://testserver"}) as client:
            start.wait(timeout=10)
            return client.post("/api/auth/owner-activation", json={
                "name": "Synthetic Owner",
                "email": "first-owner@example.com",
                "password": "Synthetic-password-01",
                "activation_code": "synthetic-activation-code",
            })

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(activate) for _ in range(2)]
        accepted, rejected = sorted(
            (attempt.result(timeout=20) for attempt in attempts),
            key=lambda response: response.status_code,
        )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["owner_activated"] is True
    cookie = accepted.cookies.get("crownpath_session")
    assert cookie
    assert rejected.status_code == 400, rejected.text
    assert rejected.json() == {"detail": "Owner activation is already complete."}
    assert not any(
        header.startswith("crownpath_session=")
        for header in rejected.headers.get_list("set-cookie")
    )

    with sessions() as db:
        owner_id, = db.scalars(select(User.user_id).where(User.role == "OWNER")).all()
        assert len(db.scalars(select(AuthToken)).all()) == 1
    assert auth.decode_access_token(cookie) == owner_id
