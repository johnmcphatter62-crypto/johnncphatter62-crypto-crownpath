"""Verify single-use Owner recovery codes through the actual sign-in route."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from crownpath import auth
from crownpath.models import AuditEvent, AuthToken, User
from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


def test_concurrent_recovery_code_sign_in_issues_one_session(isolated_logout_engine, monkeypatch):
    from fastapi.testclient import TestClient

    from crownpath import audit, main

    engine = isolated_logout_engine
    AuditEvent.__table__.create(engine)
    sessions = sessionmaker(bind=engine)
    for module in (auth, audit, main):
        monkeypatch.setattr(module, "session", sessions)
    password = "Synthetic-password-01"
    email = "recovery-owner@example.com"
    user_id = "synthetic-recovery-owner"
    with sessions.begin() as db:
        db.add(User(
            user_id=user_id, name="Synthetic Recovery Owner", email=email,
            password_hash=auth.hash_password(password), role="OWNER",
            active=True, mfa_enabled=True, mfa_secret="JBSWY3DPEHPK3PXP",
        ))
    code, = auth.generate_mfa_recovery_codes(user_id, count=1)
    start = Barrier(2)

    def sign_in():
        with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
            login = client.post("/api/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200, login.text
            assert login.json()["mfa_required"] is True
            start.wait(timeout=10)
            return client.post("/api/auth/mfa/verify", json={
                "challenge": login.json()["challenge"], "code": code,
            })

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(sign_in) for _ in range(2)]
        accepted, rejected = sorted(
            (attempt.result(timeout=20) for attempt in attempts),
            key=lambda response: response.status_code,
        )
    assert accepted.status_code == 200, accepted.text
    cookie = accepted.cookies.get("crownpath_session")
    assert cookie and auth.decode_access_token(cookie) == user_id
    assert auth.session_mfa_verified(cookie)
    assert rejected.status_code == 401, rejected.text
    assert not rejected.headers.get_list("set-cookie")
    with sessions() as db:
        tokens = db.scalars(select(AuthToken).where(AuthToken.user_id == user_id)).all()
        recovery, = [token for token in tokens if token.token_type == "MFA_RECOVERY"]
        assert recovery.used_at is not None
        assert len(tokens) == 2
