"""Disposable HTTP proof replay regression; no production payment route/provider."""
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from crownpath.payment_mfa_db_proof import (
    consume_proof, create_test_schema, issue_verified_proof, revoke_session_proofs,
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


def test_revoked_session_payment_proof_denied_at_http_probe(tmp_path):
    """Session termination revokes outstanding proofs before a simulated payment call."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_revoked_session.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        )
        revoked = revoke_session_proofs(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        )
        assert revoked == 1
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-revoked-session-probe")
        def probe():
            if not consume_proof(
                engine, token=proof, user_id="synthetic-owner",
                session_id="terminated-session",
            ):
                raise HTTPException(403, "Payment proof revoked")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            response = client.post("/isolated/payment-revoked-session-probe")
        assert response.status_code == 403
        assert provider_calls == []
    finally:
        engine.dispose()


def test_revoking_one_session_preserves_other_owner_session_proof(tmp_path):
    """Revocation must target only the terminated session, not sibling sessions."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_session_scope.db'}")
    try:
        create_test_schema(engine)
        terminated_proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        )
        active_proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="active-session",
        )
        assert revoke_session_proofs(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        ) == 1
        app = FastAPI()
        provider_calls = []
        request_scope = {"proof": terminated_proof, "session": "terminated-session"}

        @app.post("/isolated/payment-session-scope-probe")
        def probe():
            if not consume_proof(
                engine, token=request_scope["proof"], user_id="synthetic-owner",
                session_id=request_scope["session"],
            ):
                raise HTTPException(403, "Payment proof unavailable")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-session-scope-probe")
            assert denied.status_code == 403
            assert provider_calls == []
            request_scope.update(proof=active_proof, session="active-session")
            allowed = client.post("/isolated/payment-session-scope-probe")
        assert allowed.status_code == 200
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_repeated_session_revocation_is_idempotent_and_scoped(tmp_path):
    """A second revoke changes nothing and preserves another session's proof."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_repeat_revoke.db'}")
    try:
        create_test_schema(engine)
        revoked_proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        )
        other_proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="active-session",
        )
        assert revoke_session_proofs(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        ) == 1
        assert revoke_session_proofs(
            engine, user_id="synthetic-owner", session_id="terminated-session",
        ) == 0
        app = FastAPI()
        provider_calls = []
        scope = {"proof": revoked_proof, "session": "terminated-session"}

        @app.post("/isolated/payment-repeat-revoke-probe")
        def probe():
            if not consume_proof(
                engine, token=scope["proof"], user_id="synthetic-owner",
                session_id=scope["session"],
            ):
                raise HTTPException(403, "Payment proof unavailable")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-repeat-revoke-probe")
            assert denied.status_code == 403
            assert provider_calls == []
            scope.update(proof=other_proof, session="active-session")
            allowed = client.post("/isolated/payment-repeat-revoke-probe")
        assert allowed.status_code == 200
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_revocation_of_one_owner_preserves_other_owner_session_proof(tmp_path):
    """A targeted revoke must not invalidate another owner's valid proof."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_cross_owner_revoke.db'}")
    try:
        create_test_schema(engine)
        revoked_proof = issue_verified_proof(
            engine, user_id="synthetic-owner-a", session_id="shared-session-label",
        )
        other_proof = issue_verified_proof(
            engine, user_id="synthetic-owner-b", session_id="shared-session-label",
        )
        assert revoke_session_proofs(
            engine, user_id="synthetic-owner-a", session_id="shared-session-label",
        ) == 1
        app = FastAPI()
        provider_calls = []
        scope = {"proof": revoked_proof, "owner": "synthetic-owner-a"}

        @app.post("/isolated/payment-cross-owner-revoke-probe")
        def probe():
            if not consume_proof(
                engine, token=scope["proof"], user_id=scope["owner"],
                session_id="shared-session-label",
            ):
                raise HTTPException(403, "Payment proof unavailable")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-cross-owner-revoke-probe")
            assert denied.status_code == 403
            assert provider_calls == []
            scope.update(proof=other_proof, owner="synthetic-owner-b")
            allowed = client.post("/isolated/payment-cross-owner-revoke-probe")
        assert allowed.status_code == 200
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_disabled_owner_cannot_use_previously_issued_proof_at_http_probe(tmp_path):
    """Account deactivation blocks a previously issued proof before provider access."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_disabled_owner.db'}")
    try:
        create_test_schema(engine)
        proof = issue_verified_proof(
            engine, user_id="synthetic-owner", session_id="synthetic-session",
        )
        app = FastAPI()
        provider_calls = []
        account = {"active": False}  # Disabled after the proof was issued.

        @app.post("/isolated/payment-disabled-owner-probe")
        def probe():
            if not account["active"]:
                raise HTTPException(403, "Owner account disabled")
            if not consume_proof(
                engine, token=proof, user_id="synthetic-owner",
                session_id="synthetic-session",
            ):
                raise HTTPException(403, "Payment proof unavailable")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-disabled-owner-probe")
        assert denied.status_code == 403
        assert provider_calls == []
        # Deactivation must not consume the proof; revocation is a separate control.
        assert consume_proof(
            engine, token=proof, user_id="synthetic-owner",
            session_id="synthetic-session",
        ) is True
    finally:
        engine.dispose()


def test_disabled_then_reenabled_owner_cannot_reuse_old_payment_proofs(tmp_path):
    """Simulated deactivation revokes both sessions; reactivation cannot revive proofs."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_owner_reenabled.db'}")
    try:
        create_test_schema(engine)
        owner = "synthetic-owner"
        sessions = ("synthetic-session-a", "synthetic-session-b")
        proofs = {
            session: issue_verified_proof(engine, user_id=owner, session_id=session)
            for session in sessions
        }
        account = {"active": True}
        # Isolated deactivation workflow: change account state and revoke each
        # known session's proof. Production account hooks are not wired here.
        account["active"] = False
        assert sum(
            revoke_session_proofs(engine, user_id=owner, session_id=session)
            for session in sessions
        ) == 2
        account["active"] = True  # Simulate later account restoration.
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-reactivated-owner-probe/{session}")
        def probe(session: str):
            if session not in proofs or not account["active"]:
                raise HTTPException(403, "Owner access denied")
            if not consume_proof(
                engine, token=proofs[session], user_id=owner, session_id=session,
            ):
                raise HTTPException(403, "Payment proof revoked")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            for session in sessions:
                assert client.post(
                    f"/isolated/payment-reactivated-owner-probe/{session}"
                ).status_code == 403
        assert provider_calls == []
    finally:
        engine.dispose()


def test_reactivated_owner_requires_new_payment_proof_at_http_probe(tmp_path):
    """After reactivation, an old revoked proof fails; a new proof works once."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_new_proof_after_reactivation.db'}")
    try:
        create_test_schema(engine)
        owner, session = "synthetic-owner", "synthetic-session"
        old_proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        account = {"active": False}
        assert revoke_session_proofs(
            engine, user_id=owner, session_id=session,
        ) == 1
        account["active"] = True
        new_proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        app = FastAPI()
        provider_calls = []
        scope = {"proof": old_proof}

        @app.post("/isolated/payment-reactivated-new-proof-probe")
        def probe():
            if not account["active"] or not consume_proof(
                engine, token=scope["proof"], user_id=owner, session_id=session,
            ):
                raise HTTPException(403, "Fresh payment authorization required")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            assert client.post(
                "/isolated/payment-reactivated-new-proof-probe"
            ).status_code == 403
            assert provider_calls == []
            scope["proof"] = new_proof
            assert client.post(
                "/isolated/payment-reactivated-new-proof-probe"
            ).status_code == 200
            assert client.post(
                "/isolated/payment-reactivated-new-proof-probe"
            ).status_code == 403
        assert provider_calls == ["simulated-config-change"]
    finally:
        engine.dispose()


def test_reactivated_owner_new_proof_stays_bound_to_owner_and_session(tmp_path):
    """A newly issued proof cannot cross owner/session after reactivation."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_reactivated_scope.db'}")
    try:
        create_test_schema(engine)
        owner, session = "synthetic-owner-a", "reactivated-session"
        old_proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        assert revoke_session_proofs(engine, user_id=owner, session_id=session) == 1
        new_proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        app = FastAPI()
        provider_calls = []
        scope = {"owner": "synthetic-owner-b", "session": session}

        @app.post("/isolated/payment-reactivated-scope-probe")
        def probe():
            if not consume_proof(
                engine, token=new_proof, user_id=scope["owner"],
                session_id=scope["session"],
            ):
                raise HTTPException(403, "Payment proof scope mismatch")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            assert client.post("/isolated/payment-reactivated-scope-probe").status_code == 403
            assert provider_calls == []
            scope.update(owner=owner, session="other-session")
            assert client.post("/isolated/payment-reactivated-scope-probe").status_code == 403
            assert provider_calls == []
            scope.update(owner=owner, session=session)
            assert client.post("/isolated/payment-reactivated-scope-probe").status_code == 200
            assert client.post("/isolated/payment-reactivated-scope-probe").status_code == 403
        assert provider_calls == ["simulated-config-change"]
        assert not consume_proof(engine, token=old_proof, user_id=owner, session_id=session)
    finally:
        engine.dispose()


def test_fresh_proof_revoked_again_while_owner_remains_active(tmp_path):
    """A second session revocation invalidates new proof without disabling owner."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_second_revocation.db'}")
    try:
        create_test_schema(engine)
        owner, session = "synthetic-owner", "reactivated-session"
        old_proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        assert revoke_session_proofs(engine, user_id=owner, session_id=session) == 1
        fresh_proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        account = {"active": True}
        # Terminate the reactivated session again, without disabling the account.
        assert revoke_session_proofs(engine, user_id=owner, session_id=session) == 1
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-second-revocation-probe")
        def probe():
            if not account["active"] or not consume_proof(
                engine, token=fresh_proof, user_id=owner, session_id=session,
            ):
                raise HTTPException(403, "Payment proof revoked")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            denied = client.post("/isolated/payment-second-revocation-probe")
        assert denied.status_code == 403
        assert account["active"] is True
        assert provider_calls == []
        assert not consume_proof(engine, token=old_proof, user_id=owner, session_id=session)
    finally:
        engine.dispose()


def test_new_session_requires_new_proof_after_second_revocation(tmp_path):
    """Twice-revoked old session cannot authorize a newly established session."""
    engine = create_engine(f"sqlite:///{tmp_path / 'http_new_session_after_revoke.db'}")
    try:
        create_test_schema(engine)
        owner = "synthetic-owner"
        old_session, new_session = "terminated-session", "new-session"
        first_proof = issue_verified_proof(engine, user_id=owner, session_id=old_session)
        assert revoke_session_proofs(engine, user_id=owner, session_id=old_session) == 1
        second_proof = issue_verified_proof(engine, user_id=owner, session_id=old_session)
        assert revoke_session_proofs(engine, user_id=owner, session_id=old_session) == 1
        fresh_proof = issue_verified_proof(engine, user_id=owner, session_id=new_session)
        app = FastAPI()
        provider_calls = []
        scope = {"proof": second_proof, "session": new_session}

        @app.post("/isolated/payment-new-session-probe")
        def probe():
            if not consume_proof(
                engine, token=scope["proof"], user_id=owner,
                session_id=scope["session"],
            ):
                raise HTTPException(403, "New session authorization required")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        with TestClient(app) as client:
            assert client.post("/isolated/payment-new-session-probe").status_code == 403
            assert provider_calls == []
            scope.update(proof=fresh_proof, session=old_session)
            assert client.post("/isolated/payment-new-session-probe").status_code == 403
            assert provider_calls == []
            scope.update(proof=fresh_proof, session=new_session)
            assert client.post("/isolated/payment-new-session-probe").status_code == 200
            assert client.post("/isolated/payment-new-session-probe").status_code == 403
        assert provider_calls == ["simulated-config-change"]
        assert not consume_proof(engine, token=first_proof, user_id=owner, session_id=old_session)
    finally:
        engine.dispose()


def test_concurrent_requests_consume_one_payment_proof_only_once(tmp_path):
    """Concurrent HTTP requests cannot both consume the same SQLite proof."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    engine = create_engine(
        f"sqlite:///{tmp_path / 'http_concurrent_proof.db'}",
        connect_args={"timeout": 10},
    )
    try:
        create_test_schema(engine)
        owner, session = "synthetic-owner", "synthetic-session"
        proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-concurrent-proof-probe")
        def probe():
            if not consume_proof(engine, token=proof, user_id=owner, session_id=session):
                raise HTTPException(403, "Payment proof already consumed")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        barrier = Barrier(2)

        def request_once():
            barrier.wait(timeout=10)
            with TestClient(app) as client:
                return client.post("/isolated/payment-concurrent-proof-probe").status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: request_once(), range(2)))
        assert sorted(results) == [200, 403]
        assert provider_calls == ["simulated-config-change"]
        assert not consume_proof(engine, token=proof, user_id=owner, session_id=session)
    finally:
        engine.dispose()


def test_concurrent_revocation_and_requests_allow_at_most_one_change(tmp_path):
    """Racing revocation and HTTP requests cannot duplicate a proof's use."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    engine = create_engine(
        f"sqlite:///{tmp_path / 'http_revocation_race.db'}",
        connect_args={"timeout": 10},
    )
    try:
        create_test_schema(engine)
        owner, session = "synthetic-owner", "synthetic-session"
        proof = issue_verified_proof(engine, user_id=owner, session_id=session)
        app = FastAPI()
        provider_calls = []

        @app.post("/isolated/payment-revocation-race-probe")
        def probe():
            if not consume_proof(engine, token=proof, user_id=owner, session_id=session):
                raise HTTPException(403, "Payment proof unavailable")
            provider_calls.append("simulated-config-change")
            return {"changed": True}

        barrier = Barrier(3)

        def request_once():
            barrier.wait(timeout=10)
            with TestClient(app) as client:
                return client.post("/isolated/payment-revocation-race-probe").status_code

        def revoke_once():
            barrier.wait(timeout=10)
            return revoke_session_proofs(engine, user_id=owner, session_id=session)

        with ThreadPoolExecutor(max_workers=3) as pool:
            first = pool.submit(request_once)
            second = pool.submit(request_once)
            revocation = pool.submit(revoke_once)
            results = [first.result(), second.result()]
            revoked_count = revocation.result()
        # If revocation wins, neither request succeeds; otherwise exactly one may.
        assert all(status in (200, 403) for status in results)
        assert results.count(200) <= 1
        assert results.count(403) >= 1
        assert len(provider_calls) == results.count(200)
        assert revoked_count in (0, 1)
        with TestClient(app) as client:
            assert client.post("/isolated/payment-revocation-race-probe").status_code == 403
        assert not consume_proof(engine, token=proof, user_id=owner, session_id=session)
    finally:
        engine.dispose()
