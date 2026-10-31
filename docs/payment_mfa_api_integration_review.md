# Payment MFA API integration review — NOT YET ENABLED

Reviewed existing `crownpath/main.py` owner authentication paths on the isolated branch.

## Findings
- `current_user(request)` reads the signed `crownpath_session` cookie, resolves the user, checks active status and role-access approval.
- `require_permission(permission)` checks role permission after authentication.
- `/api/auth/mfa/verify` verifies a login MFA challenge and then issues a session cookie.
- `/api/auth/mfa/setup` and `/api/auth/mfa/enable` handle authenticator enrollment.
- No trusted payment step-up endpoint exists yet; `recent_mfa_verified` must **never** be sourced from client JSON, query strings, or headers.

## Integration design
1. Implement a dedicated owner-only, CSRF-protected step-up route that uses the **existing authenticated cookie**, re-checks role, active status, MFA enabled, and `payments.configure`.
2. Accept an authenticator code over HTTPS and verify it server-side. Reusing `verify_mfa_code` may consume recovery codes; decide explicitly whether recovery codes are acceptable for sensitive payment changes.
3. Derive a stable session identifier from the verified session token server-side; never accept a client-selected session ID.
4. Only after MFA succeeds, call a production-hardened proof issuer; return a short-lived opaque proof with `Cache-Control: no-store` and redact it from logs.
5. On the payment settings endpoint, derive user and session again from the cookie, consume the proof atomically, and enforce owner-only access, CSRF, and rate limiting. Payment-provider changes need separate validation and audit events.
6. Add a proper migration for shared proof storage with cleanup, indexes, expiry, and retention policy. The existing `payment_mfa_proofs_test` table is test-only.
7. Require negative tests for forged client booleans, session swapping, logout/session invalidation, missing CSRF, replay, and concurrent consumption.

**Release gate:** Keep payment endpoints and production changes blocked until session invalidation, CSRF, provider configuration, migrations, and auditing are designed and tested. No secrets or production data needed for this review.
