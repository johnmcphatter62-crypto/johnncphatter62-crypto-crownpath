"""Concurrent synthetic proof consumption: exactly one request may succeed.

These tests cover the in-memory test primitive only, not database atomicity.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from crownpath.payment_mfa_proof import EphemeralPaymentMfaProofs

def test_concurrent_consume_is_single_use():
    proofs = EphemeralPaymentMfaProofs()
    token = proofs.issue_after_verified_mfa("owner-1")
    barrier = Barrier(8)

    def consume_once(_):
        barrier.wait(timeout=5)
        return proofs.consume(token, "owner-1")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(consume_once, range(8)))
    assert results.count(True) == 1
    assert results.count(False) == 7

def test_wrong_purpose_consumes_proof_fail_closed():
    proofs = EphemeralPaymentMfaProofs()
    token = proofs.issue_after_verified_mfa("owner-1")
    assert not proofs.consume(token, "owner-1", purpose="staff.manage")
    assert not proofs.consume(token, "owner-1")
