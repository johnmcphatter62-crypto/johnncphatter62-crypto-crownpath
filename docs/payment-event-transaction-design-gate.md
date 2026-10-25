# CrownPath — Persistent Payment Event Design Gate

Status: DESIGN ONLY. No production payment implementation, provider integration, or database migration is authorized.

## Core records
- `payment_orders`: internal order ID, trusted catalog item and server-calculated amount/currency, lifecycle state, timestamps, and authorized learner reference.
- `payment_events`: provider identifier, provider event ID, internal order ID, event type, verification result, received time, processing outcome. Unique constraint on (provider, provider event ID).
- `enrollment_entitlements`: order ID and learner/course ID with uniqueness ensuring one entitlement per qualifying purchase. Never grant enrollment from a browser callback alone.

## Atomic processing rules
1. Provider adapter validates the authentic signed webhook using the provider's documented raw-body signature protocol, including timestamp/replay checks. A caller-supplied boolean alone is insufficient.
2. Begin a database transaction; insert event with unique (provider, event ID) key. For a duplicate, return the prior processing result without repeating fulfillment.
3. Lock the associated order row for update in PostgreSQL. Confirm provider order reference, trusted catalog amount, currency, and legal state transition.
4. Apply payment transition and eligible enrollment entitlement inside the **same transaction**; rollback everything on any failure.
5. Record metadata-only audit evidence. Commit before acknowledging the event to the provider.
6. Handle out-of-order events, retries, refunds, and disputes using a documented reconciliation workflow. Never trust client-supplied prices, payout addresses, or return URLs.

## Test plan — disposable databases and synthetic identities only
- Two simultaneous deliveries of one signed synthetic event result in exactly one transition and one entitlement.
- Two different event IDs attempting the same successful payment cannot duplicate enrollment.
- Invalid signature, wrong amount/currency, unknown order, altered return origin, and out-of-order transitions are rejected.
- Forced transaction failure leaves no partial event, state change, or entitlement.
- A retry after rollback succeeds exactly once.
- Separate learner accounts cannot read or modify each other's orders.
- Provider event IDs are unique per provider; collisions across different providers do not conflate records.

## Implementation prerequisites
- Choose and authorize a payment provider and define its verified webhook semantics.
- Review migration compatibility and the existing SQLAlchemy transaction conventions.
- Keep all tests isolated from production and payment credentials.
- Require Owner MFA, independent security review, and explicit release approval.

## Evidence and limitations
CI #546 confirmed five tests of the provider-neutral in-memory policy rules. Those tests **do not** establish persisted idempotency, actual cryptographic webhook verification, or payment readiness.

Related: `docs/payment-integrity-learner-privacy-review-gate.md` and `docs/payment-integration-source-discovery.md`.
