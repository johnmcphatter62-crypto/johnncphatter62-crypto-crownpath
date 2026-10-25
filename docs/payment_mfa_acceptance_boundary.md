# Payment MFA proof prototype — current acceptance boundary

## Verified in CI #581
- Disposable SQLite/PostgreSQL database-backed hashed, expiring, one-use proof behavior.
- User and session scope, purpose binding, wrong-token denial, replay prevention.
- Concurrent consumption and revocation tests, including consume-vs-revoke ordering.
- CI #581: application 250 passed; owner-access and migration jobs passed.

## Not yet implemented — release blockers
1. Production-ready server-verified step-up MFA challenge endpoint and authorization checks.
2. Trusted session identifier derived from validated authentication; logout and proof invalidation in one consistent transaction or atomic session-revocation check.
3. CSRF and request rate limiting, provider configuration validation, audit logging, and alerting.
4. Durable schema migration replacing `payment_mfa_proofs_test` and a cleanup/retention policy.
5. Integration tests using the actual authenticated routes, logout, and payment configuration handlers, including a simulated failed transaction.
6. Review of the policy for recovery-code use during payment changes and owner MFA enrollment readiness.

**Do not deploy or enable payment configuration** based on prototype CI results. The proof issuer currently assumes a separate trusted MFA check; it does not perform that check itself. The proof revocation primitive does not automatically revoke login sessions.
