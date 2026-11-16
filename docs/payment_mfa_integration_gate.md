# CrownPath payment MFA integration gate (design only)

Status: **BLOCKED for production**. This document does not authorize deployment or payment processing.

## Verified source observations
- `crownpath/auth.py::verify_mfa_code(user_id, code)` verifies TOTP or consumes a recovery code, and includes account lockout handling.
- `crownpath/main.py` contains the existing MFA login challenge flow and server-side `require_permission` dependency.
- `crownpath/payment_access.py` currently requires an externally supplied `recent_mfa_verified` boolean. A caller-provided HTTP boolean is **not trustworthy**.
- `crownpath/payment_mfa_proof.py` is an in-memory test primitive. It is **not production safe**, is not wired to authentication, and must not be used across workers.

## Required implementation before enabling payment configuration
1. Add a dedicated authenticated **step-up MFA** endpoint for the currently logged-in owner, not a user-supplied user ID. Require `payments.configure` and `mfa_enabled`.
2. Validate the submitted code on the server using the existing `verify_mfa_code` function; never expose or log codes, recovery codes, or MFA secrets.
3. After successful verification, issue an opaque, short-lived, one-use proof scoped to the owner ID, current session ID, and `payments.configure` purpose. Persist only a keyed hash of the proof in shared database storage.
4. Consume proof **atomically** inside a transaction with expiry and used-at conditions; reject reuse, expiration, wrong user, wrong session, and wrong purpose. Apply rate limiting, CSRF protections, and audit events.
5. For payout changes, use an independent trusted payment-provider confirmation and a cooling-off or dual-control policy where appropriate. Never accept payout account numbers from untrusted client assertions without provider-side validation.
6. Build endpoints only after a payment provider, threat model, and transaction schema are chosen. Keep production payment functionality disabled by default.

## Test acceptance criteria
- No owner session: 401. Non-owner or inactive account: 403. Owner without MFA: 403.
- MFA failure, expired proof, wrong session, wrong purpose, replay: denied.
- Two concurrent uses of one proof: **exactly one** may succeed.
- Every authorized sensitive change creates a redacted audit event.
- No production database, live credentials, or real transactions used in tests.

Do not merge the experimental proof into a production payment route. This file is a review checklist, not an implementation approval.
