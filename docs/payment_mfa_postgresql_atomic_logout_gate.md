# Atomic logout PostgreSQL verification gate

Status: **BLOCKED for production integration**. This document specifies isolated verification; it does not run PostgreSQL, migrate an application database, or activate payments.

## Required isolated PostgreSQL checks

1. Provision a disposable PostgreSQL instance with synthetic owner, session, and payment-proof rows. Never reuse a configured CrownPath application database.
2. Execute session revocation and matching payment-proof revocation in **one transaction and one database connection**. Assert rollback restores both records if an injected failure occurs between updates.
3. Run two concurrent logout transactions. Exactly one may transition the active session to revoked; the second must report no active session.
4. Race payment-proof consumption against logout. Check both commit orders and ensure a proof is never accepted **after** a committed logout. Proof consumption must authoritatively check the session within the same transactional boundary; the current experimental `consume_proof` does **not** do so.
5. Test expiration, cross-owner and cross-session IDs, deadlock/lock-timeout retries, and transaction isolation. Confirm database uniqueness and indexes.
6. Verify password changes invalidate every affected session and its proofs; compare actual application auth behavior to the proposed adapter.
7. Confirm no client-provided MFA or session-active boolean can authorize payment changes. Require fresh, server-verified MFA and CSRF enforcement.
8. Inspect logs to ensure no session tokens, proof tokens, signing secrets, or recovery codes are emitted.

## Explicit limitations

The current `payment_mfa_atomic_logout_test_adapter` is test-only and uses a disposable schema. Its transaction covers logout and proof revocation but **does not make the separate proof-consumption path session-aware or transactionally coupled**. A consume-first operation may be valid before logout commits; a consume-after-logout authorization must be denied through a server-side active-session check. Do not promote the adapter to production until PostgreSQL integration tests and route-level security review pass.

Release gate: **BLOCKED**. Draft PR remains unmerged. No live database or payment access.
