# CrownPath payment proof revocation: next isolated acceptance gate

Status: design checkpoint only. No production route, credential, migration, provider, deployment or merge changed.

## Verified gap
- The existing password-change authentication function invalidates the user's SESSION rows.
- The experimental payment proof table is separate and has no automatic cascade from those rows.
- The isolated regression at commit f8b7bc3 demonstrates that a proof can still be consumed directly after the associated session is invalidated.
- Existing atomic logout test adapter demonstrates transactional coordination but uses a plain SHA-256 session fixture rather than the application's HMAC session-hash format.

## Required acceptance tests
1. In a disposable database with actual User and AuthToken ORM rows, issue two synthetic payment proofs for two distinct Owner A sessions and a third proof for Owner B.
2. Simulate password change in a single database transaction: update the password hash, invalidate Owner A SESSION rows and invalidate Owner A's outstanding payment proofs. Verify Owner B is unaffected.
3. Inject a failure after session invalidation and verify transaction rollback preserves the original password hash, sessions and proofs.
4. Verify no proof for Owner A can be consumed after the successful transaction; a replay or mismatched session must also fail.
5. Use HMAC-SHA256 with the `session:` prefix for test session hashes, matching `auth._hash_session_id`. Never use real session identifiers or secrets.
6. Explicitly verify that a payment-proof consumption path cannot bypass a current, authoritative session check and coordinated revocation ordering.

## Release blockers
- The transaction must be implemented and reviewed against the actual application's database engine and auth lifecycle, not just a synthetic adapter.
- The existing proof consumption function does not independently verify that the authenticated session remains active.
- Concurrent logout/password reset versus proof consumption needs deterministic, fail-closed ordering.
- Fresh payment-specific MFA, CSRF/origin enforcement, provider verification, audit and independent security review remain required.

Production payment integration: BLOCKED.
