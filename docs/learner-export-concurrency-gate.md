# CrownPath learner export — concurrent request safety gate

Status: **OPEN**. The hourly export limit currently counts SUCCESS audit events in a one-hour window. This is not an atomic reservation or lock.

## Identified race
Two or more simultaneous requests can read the same count before any request writes its SUCCESS audit event. If the account has four prior successes, both may pass the check, resulting in more than five exports within an hour. CI #511 verifies sequential behavior, **not** distributed or concurrent correctness.

## Required remediation
- Introduce an atomic, database-enforced export quota reservation or dedicated rate-limit service shared across application instances.
- Reserve quota **before** retrieving or returning personal data. Decide whether failures release the reservation, with documented retry behavior.
- Enforce an upper bound on pending exports and prevent indefinite resource holding.
- Persist an audit event for successful, failed, and quota-rejected attempts without sensitive content.
- Use UTC and define a clear rolling-hour policy; test expiry at window boundaries.
- Exercise at least ten concurrent requests against an isolated PostgreSQL database and assert at most five successful responses, with remaining requests returning HTTP 429.
- Test separate users do not consume one another's quota and verify multi-instance behavior.
- Test network disconnects, database errors, and process restarts for quota correctness.

## Release decision
Do not treat the current rate limiter as a production security boundary until the atomicity tests and independent review pass. Keep PR #46 in draft and production unchanged.
