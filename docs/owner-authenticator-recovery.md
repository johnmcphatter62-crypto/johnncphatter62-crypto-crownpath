# Owner authenticator replacement

A saved recovery code currently completes MFA sign-in once. Replacing a lost authenticator requires a separate recovery procedure when the Owner has lost access to both the authenticator and the saved codes.

## Ownership verification

Before launch, designate an operator with access to an independently controlled recovery channel registered while the Owner still has access. Record who may use that channel, how changes to it are approved, and who can review the recovery decision. A request, password, or claimed email address alone cannot establish ownership. If the designated channel is unavailable, keep the request pending until ownership can be verified through an approved alternative.

Record the approval reference, target Owner, verifier, expiration and outcome. Keep identity evidence in restricted storage and keep secrets and identity documents out of application logs. Bind approval to one account and one reset and consume it once.

## Reset and enrollment

1. Atomically consume the approval, invalidate all old sessions and outstanding authentication challenges, revoke old recovery codes, retire the old authenticator secret, and record the reset. Serialize this transition with sign-in and session issuance so an in-flight pre-reset login cannot create a valid session afterward.
2. Give the verified Owner a short-lived enrollment credential through the approved recovery channel. Scope the credential to MFA enrollment. Ordinary sign-in during recovery must not turn a password alone into an enrollment credential.
3. Require proof from the new authenticator. Consume the enrollment credential, enable MFA, issue fresh recovery codes and record completion. Restore privileged access only after the new MFA proof.

## Release evidence

- No-code recovery succeeds only with valid ownership approval and new authenticator proof.
- Missing, expired, reused and wrong-account approvals leave credentials unchanged.
- Old sessions, outstanding challenges, authenticator codes and recovery codes fail after reset, including in-flight login attempts.
- Failed persistence rolls back the entire reset. Concurrent requests consume one approval once.
- Abandoned enrollment leaves privileged access blocked. The verified Owner can resume through the approved recovery channel.
- Audits identify the decision and outcome without exposing secrets.

Validate on a disposable database. The choice of recovery operator and verification channel is open. This design adds no reset endpoint or production recovery capability.
