# Payment MFA session adapter — remaining real integration boundary

Checkpoint after CI #614: 390 application tests passed; owner-access and migration jobs passed.

## Confirmed

The isolated `payment_mfa_signed_session_test_adapter` validates a signed JWT and calls trusted session/user validators. Its unit tests reject malformed claims, invalid tokens, expired tokens, and explicit validator denials.

## Not yet verified

The test adapter's callbacks currently use synthetic sets and lambdas. No test yet establishes that these callbacks are bound to the application's actual `AuthToken` row and `User` record, and no payment route consumes the adapter. It would be incorrect to treat 390 passing tests as end-to-end payment protection.

## Next engineering milestone: authoritative disposable database adapter

1. Use existing `auth.py` JWT signature and purpose checks, then validate the `jti` against the hashed `AuthToken` row in a disposable database.
2. Re-fetch active user and role in the same controlled test environment; do not trust request-supplied user IDs.
3. Test logout and password-reset revocation, including concurrent access.
4. Define transaction boundaries for session revocation plus payment-proof revocation before any HTTP route or payment-provider integration.
5. Review real MFA step-up, CSRF, audit, provider-account ownership and destination integrity separately.

**Production release: BLOCKED.** Keep draft PR #47 unmerged; do not deploy, access secrets, or connect live payments.
