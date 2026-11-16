# CrownPath — scoped device access readiness review

**Decision: BLOCKED for production.** The staged school-scoped policy and
isolated HTTP harness are not an approved production feature. CI success only
establishes the currently tested behavior.

## What is verified on the development branch

- School membership resolves to exactly one active school, with an active
  approving Owner holding a matching, unrevoked, unexpired school grant.
- Device visibility is restricted to trusted records for the verified learner
  and school; forged query parameters do not grant scope.
- Revocation, expiration, cross-school mismatch and ambiguous memberships
  deny access in disposable database and isolated HTTP tests.
- Tests inspect the real application router to guard against accidentally
  registering known staged device endpoints.
- No actual Bluetooth/Wi-Fi discovery, camera capture or media transmission
  is implemented by these staged functions.

## Release blockers

1. **Authentication binding:** Wire only to the real server-verified session;
   reject inactive accounts and unapproved roles. Never accept school or user
   identifiers from request bodies or query parameters.
2. **Authorization lifecycle:** Define and enforce when school Owner grants
   become valid relative to membership approval, including retroactive
   revocation semantics. Current staged resolver checks current Owner grant,
   not historical grant at the original approval instant.
3. **Trusted device source:** Specify a server-managed, school-scoped device
   registry with approval provenance, revocation, expiration, transport
   restrictions and audit records. Synthetic dictionaries are not sufficient.
4. **Consent and privacy:** Require explicit, revocable per-session permission
   for Bluetooth/Wi-Fi and separately for camera/microphone. No hidden
   scanning, recording or collection of biometric/health information.
5. **Browser and hardware tests:** Verify permission prompts, denial,
   disconnect, idle timeout, and browser support on supported devices.
6. **Security verification:** Test actual authenticated application routes,
   cross-tenant access, race conditions, failure modes, logging, and data
   minimization. Do not treat test-only FastAPI routes as live coverage.
7. **Database release:** Validate upgrade/downgrade, constraints, and default
   deny behavior against disposable PostgreSQL. Plan data backfill without
   granting Owner authority automatically.
8. **Owner sign-off:** Review the access model, user experience, data
   retention, and release checklist; explicitly approve merge and deployment.

## Next safe milestone

Write database-backed tests for temporal ordering: an Owner's school grant
must not be retroactively treated as authority for a learner approval issued
before that grant. Fix the staged resolver if tests expose a gap. Keep
production endpoints, hardware access and payments unchanged.
