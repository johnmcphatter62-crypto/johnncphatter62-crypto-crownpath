"""Disposable HTTP proof replay regression; no production payment route/provider."""
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from crownpath.payment_mfa_db_proof import (
    consume_proof, create_test_schema, issue_verified_proof,
)


def test_payment_proof_replay_denied_before_simulated_provider_call(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'http_replay.db'}")
    try:
        create_test_schema(engine)
        # Synthetic proof is issued as though trusted MFA verification succeeded.
        # This is NOT a real MFA verifier or signed-session authentication test.
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="synthetic-session",
        )
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-replay-probe")
        def probe():
            # Identity/session are fixed trusted test fixtures, never request fields.
            if not consume_proof(
                engine, token=proof, user_id="synthetic-owner",
                session_id="synthetic-session",
            ):
                raise HTTPException(403, "Payment proof unavailable")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            first = client.post("/isolated/payment-replay-probe")
            second = client.post("/isolated/payment-replay-probe")
        assert first.status_code == 200
        assert second.status_code == 403
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_expired_payment_proof_rejected_at_isolated_http_probe(tmp_path):
    """Expired synthetic proof must not reach a simulated payment provider."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_expired.db'}")
    try:
        create_test_schema(engine)
        issued_at = 1_700_000_000
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="synthetic-session",
            now=issued_at, ttl_seconds=30,
        )
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-expired-probe")
        def probe():
            if not consume_proof(
                engine, token=proof, user_id="synthetic-owner",
                session_id="synthetic-session", now=issued_at + 31,
            ):
                raise HTTPException(403, "Payment proof expired")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            response = client.post("/isolated/payment-expired-probe")
        assert response.status_code == 403
        assert provider_calls == []
    finally:
        engine.dispose()


def test_payment_proof_cannot_be_substituted_into_another_session(tmp_path):
    """Wrong session denies at HTTP probe without consuming the rightful proof."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_session_swap.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="original-session",
        )
        app = FastAPI()
        provider_calls = []
        # These server-selected session identities simulate authenticated context;
        # the request never supplies the authoritative session identifier.
        current_session = {"id": "different-session"}

        @app.post("/isolated/payment-session-probe")
        def probe():
            if not consume_proof(
                engine, token=proof, user_id="synthetic-owner",
                session_id=current_session["id"],
            ):
                raise HTTPException(403, "Payment proof session mismatch")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-session-probe")
            assert denied.status_code == 403
            assert provider_calls == []
            current_session["id"] = "original-session"
            allowed = client.post("/isolated/payment-session-probe")
        assert allowed.status_code == 200
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_payment_proof_cannot_cross_owner_identity_at_http_probe(tmp_path):
    """A proof scoped to Owner A must not authorize Owner B or be consumed."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_owner_swap.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner-a", session_id="original-session",
        )
        app = FastAPI()
        provider_calls = []
        # Server-owned identity fixture, never accepted from request payload.
        identity = {"user_id": "synthetic-owner-b"}

        @app.post("/isolated/payment-owner-probe")
        def probe():
            if not consume_proof(
                engine, token=proof, user_id=identity["user_id"],
                session_id="original-session",
            ):
                raise HTTPException(403, "Payment proof owner mismatch")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-owner-probe")
            assert denied.status_code == 403
            assert provider_calls == []
            identity["user_id"] = "synthetic-owner-a"
            allowed = client.post("/isolated/payment-owner-probe")
        assert allowed.status_code == 200
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_payment_proof_rejected_for_wrong_purpose_at_http_probe(tmp_path):
    """Payment-config proof must not authorize a different synthetic operation."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_wrong_purpose.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="synthetic-session",
        )
        app = FastAPI()
        provider_calls = []
        operation = {"purpose": "payments.refund"}

        @app.post("/isolated/payment-purpose-probe")
        def probe():
            if not consume_proof(
                engine, token=proof, user_id="synthetic-owner",
                session_id="synthetic-session", purpose=operation["purpose"],
            ):
                raise HTTPException(403, "Payment proof purpose mismatch")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-purpose-probe")
            assert denied.status_code == 403
            assert provider_calls == []
            operation["purpose"] = "payments.configure"
            allowed = client.post("/isolated/payment-purpose-probe")
        assert allowed.status_code == 200
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()
