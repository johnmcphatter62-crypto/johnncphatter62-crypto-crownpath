"""Tests for isolated MFA proof mechanics; no real authenticator or provider."""
from crownpath.payment_mfa_proof import EphemeralPaymentMfaProofs

def test_single_use_and_owner_binding():
    proofs = EphemeralPaymentMfaProofs()
    token = proofs.issue_after_verified_mfa("owner-1")
    assert not proofs.consume(token, "other-user")
    assert not proofs.consume(token, "owner-1")

def test_valid_once():
    proofs = EphemeralPaymentMfaProofs()
    token = proofs.issue_after_verified_mfa("owner-1")
    assert proofs.consume(token, "owner-1")
    assert not proofs.consume(token, "owner-1")

def test_expiration():
    now = [100.]
    proofs = EphemeralPaymentMfaProofs(clock=lambda: now[0], ttl_seconds=120)
    token = proofs.issue_after_verified_mfa("owner-1")
    now[0] = 221.
    assert not proofs.consume(token, "owner-1")
