# Payment MFA: actual ORM validation checkpoint (CI #624)

CI #624 passed: 397 application tests plus successful owner-access and migration jobs.

## Verified in disposable SQLite

Tests now exercise CrownPath's real `User` and `AuthToken` ORM tables for:
- signed JWT validation with database-backed session revocation;
- rejection of expired database sessions;
- rejection of inactive users;
- rejection of a JWT subject that does not own the referenced database session.

These tests use synthetic JWT signing keys, test users, and isolated databases. They do **not** query the production database or establish production route security.

## Next meaningful integration gate

Implement and test an adapter to the existing `crownpath.auth` session lifecycle using dependency injection or test-only database override. Do not duplicate the real session-validation logic in production. Specifically:
1. Prove the application's actual `decode_access_token` and `revoke_access_token` behavior in an isolated database.
2. Bind any payment proof to the signed JWT's authoritative `jti`, not a client-supplied session identifier.
3. Coordinate logout/password reset with proof revocation and test concurrent consume/logout behavior.
4. Require independently verified fresh MFA, CSRF protection, audit, and payment-destination integrity before a real payment route is considered.

**Production release: BLOCKED.** Keep draft PR #47 unmerged and avoid deployments, live credentials, and payment activation.
