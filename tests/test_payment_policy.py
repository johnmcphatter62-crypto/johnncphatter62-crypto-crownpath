"""Synthetic-only tests for provider-neutral payment rules."""
import unittest
from decimal import Decimal

from crownpath.payment_policy import (
    PaymentOrder, PaymentState, apply_verified_event,
    validate_return_url, verify_catalog_amount,
)


class PaymentPolicyTests(unittest.TestCase):
    def setUp(self):
        self.order = PaymentOrder("synthetic-order", Decimal("29.00"), "USD")

    def event(self, order, event_id, event_type, **changes):
        payload = dict(
            event_id=event_id, event_type=event_type, signature_verified=True,
            provider_order_id="synthetic-order",
            provider_amount=Decimal("29.00"), provider_currency="USD",
        )
        payload.update(changes)
        return apply_verified_event(order, **payload)

    def test_valid_lifecycle_and_duplicate(self):
        pending = self.event(self.order, "e1", "checkout.started")
        self.assertEqual(pending.state, PaymentState.PENDING)
        self.assertEqual(self.event(pending, "e1", "checkout.started"), pending)
        paid = self.event(pending, "e2", "payment.succeeded")
        self.assertEqual(paid.state, PaymentState.PAID)
        refunded = self.event(paid, "e3", "payment.refunded")
        self.assertEqual(refunded.state, PaymentState.REFUNDED)
        with self.assertRaises(ValueError):
            self.event(refunded, "e4", "payment.succeeded")

    def test_forged_event_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unverified"):
            self.event(self.order, "e1", "checkout.started", signature_verified=False)

    def test_amount_currency_and_order_tampering_rejected(self):
        for changed in (
            {"provider_amount": Decimal("0.01")},
            {"provider_currency": "EUR"},
            {"provider_order_id": "another-order"},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                self.event(self.order, "e1", "checkout.started", **changed)
        self.assertFalse(verify_catalog_amount(Decimal("1"), Decimal("29")))
        self.assertTrue(verify_catalog_amount(Decimal("29"), Decimal("29")))

    def test_out_of_order_and_repeat_success_rejected(self):
        with self.assertRaises(ValueError):
            self.event(self.order, "e1", "payment.succeeded")
        pending = self.event(self.order, "e1", "checkout.started")
        paid = self.event(pending, "e2", "payment.succeeded")
        with self.assertRaises(ValueError):
            self.event(paid, "e3", "payment.succeeded")

    def test_redirect_origin_allowlist(self):
        allowed = frozenset({"https://crownpath.example"})
        self.assertTrue(validate_return_url("https://crownpath.example/checkout/return", allowed))
        for url in (
            "http://crownpath.example/return",
            "https://crownpath.example.evil.test/return",
            "https://evil.test@crownpath.example/return",
            "https://crownpath.example:8443/return",
            "https://crownpath.example/return#secret",
            "//crownpath.example/return",
        ):
            with self.subTest(url=url):
                self.assertFalse(validate_return_url(url, allowed))


if __name__ == "__main__":
    unittest.main()
