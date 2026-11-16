"""Stale HTTP setup snapshot after real enrollment commit on disposable PostgreSQL."""
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from tests.test_payment_mfa_postgresql_atomic_logout import isolated_logout_engine


def test_postgres_stale_setup_preserves_completed_enrollment(isolated_logout_engine, monkeypatch):
    import pyotp
    from fastapi.testclient import TestClient
    import crownpath.auth as auth
    import crownpath.main as main
    from crownpath.models import AuthToken, User

    engine = isolated_logout_engine
    monkeypatch.setattr(auth, "session", sessionmaker(bind=engine))
    monkeypatch.setattr(main, "session", sessionmaker(bind=engine))
    monkeypatch.setattr(auth, "SECRET_KEY", "synthetic-stale-mfa-setup-key")
    with Session(engine) as db:
        db.add(User(
            user_id="stale-setup-owner", name="Synthetic Owner",
            email="stale-setup@example.invalid", password_hash="synthetic-only",
            role="OWNER", active=True, mfa_enabled=False,
        ))
        db.commit()
    enrollment_token = auth.create_access_token("stale-setup-owner")

    def recovery_hashes():
        with Session(engine) as db:
            return sorted(db.scalars(sa.select(AuthToken.token_hash).where(
                AuthToken.user_id == "stale-setup-owner",
                AuthToken.token_type == "MFA_RECOVERY",
            )).all())

    with TestClient(main.app, headers={"Origin": "http://testserver"}) as client:
        client.cookies.set("crownpath_session", enrollment_token)
        setup = client.post("/api/auth/mfa/setup")
        assert setup.status_code == 200, setup.text
        original_secret = setup.json()["secret"]
        before_hashes = []
        calls = []
        real_setup = auth.start_mfa_setup

        def enable_after_dependency_snapshot(user_id):
            # The real current_user dependency has already read mfa_enabled=False.
            # Commit the competing enrollment before its pending setup writes.
            calls.append(user_id)
            codes = auth.enable_mfa(user_id, pyotp.TOTP(original_secret).now())
            assert len(codes) == 8
            before_hashes.extend(recovery_hashes())
            return real_setup(user_id)

        with patch.object(main, "start_mfa_setup", side_effect=enable_after_dependency_snapshot):
            stale = client.post("/api/auth/mfa/setup")
        assert calls == ["stale-setup-owner"]
        assert stale.status_code == 409, stale.text
        assert "secret" not in stale.json()
        assert original_secret not in stale.text
        assert not any(
            "crownpath_session=" in header for header in stale.headers.get_list("set-cookie")
        )
        enabled = auth.get_user_by_id("stale-setup-owner")
        assert enabled["mfa_enabled"] is True
        assert enabled["mfa_secret"] == original_secret
        assert len(before_hashes) == 8 and len(set(before_hashes)) == 8
        assert recovery_hashes() == before_hashes
        # Account enrollment does not upgrade the older session's assurance.
        assert auth.decode_access_token(enrollment_token) == "stale-setup-owner"
        assert auth.session_mfa_verified(enrollment_token) is False
        assert client.get("/api/audio/stations").status_code == 403
        repeated = client.post("/api/auth/mfa/setup")
        assert repeated.status_code == 409
        assert recovery_hashes() == before_hashes
