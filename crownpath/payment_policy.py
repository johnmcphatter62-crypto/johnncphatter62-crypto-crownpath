"""Provider-neutral payment decision rules. No processor calls or payment collection.

This module intentionally does not activate enrollment or move funds.
"""
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from urllib.parse import urlsplit


class PaymentState(str, Enum):
    CREATED = "CREATED"
    PENDING = "PENDING"
    PAID = "PAID"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


@dataclass(frozen=True)
class PaymentOrder:
    order_id: str
    catalog_price: Decimal
    currency: str
    state: PaymentState = PaymentState.CREATED
    provider_event_id: str | None = None


def validate_return_url(url: str, allowed_origins: frozenset[str]) -> bool:
    """Allow exact HTTPS origins and no embedded credentials or URL fragments."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return False
        if parsed.fragment or parsed.port not in (None, 443):
            return False
        origin = f"https://{parsed.hostname.lower()}"
        return origin in allowed_origins and bool(parsed.path.startswith("/"))
    except (TypeError, ValueError, AttributeError):
        return False


def verify_catalog_amount(client_amount: Decimal, catalog_amount: Decimal) -> bool:
    """Client-submitted prices are never authoritative."""
    return (
        isinstance(client_amount, Decimal)
        and isinstance(catalog_amount, Decimal)
        and catalog_amount >= Decimal("0")
        and client_amount == catalog_amount
    )


def apply_verified_event(
    order: PaymentOrder,
    *,
    event_id: str,
    event_type: str,
    signature_verified: bool,
    provider_order_id: str,
    provider_amount: Decimal,
    provider_currency: str,
) -> PaymentOrder:
    """Pure state transition; caller must verify signatures with provider SDK.

    Does not persist event IDs or guarantee cross-process idempotency.
    """
    if not signature_verified:
        raise ValueError("Unverified payment event")
    if not event_id or provider_order_id != order.order_id:
        raise ValueError("Payment order mismatch")
    if provider_amount != order.catalog_price or provider_currency != order.currency:
        raise ValueError("Payment amount or currency mismatch")
    if event_id == order.provider_event_id:
        return order
    if order.state == PaymentState.REFUNDED:
        raise ValueError("Refunded order is terminal")
    transitions = {
        (PaymentState.CREATED, "checkout.started"): PaymentState.PENDING,
        (PaymentState.PENDING, "payment.succeeded"): PaymentState.PAID,
        (PaymentState.PENDING, "payment.failed"): PaymentState.FAILED,
        (PaymentState.PAID, "payment.refunded"): PaymentState.REFUNDED,
    }
    next_state = transitions.get((order.state, event_type))
    if next_state is None:
        raise ValueError("Invalid payment transition")
    return PaymentOrder(
        order_id=order.order_id, catalog_price=order.catalog_price,
        currency=order.currency, state=next_state, provider_event_id=event_id,
    )
