# CrownPath HTTPS & Authentication Security Acceptance Record

**Status:** NOT APPROVED — review template only. No production deployment or live penetration test has occurred.

## Evidence requirements

| Gate | Required evidence | Current assessment |
| --- | --- | --- |
| CI isolation | Successful application, owner-access, and migration jobs against disposable PostgreSQL | Automated CI success reported; preserve workflow run link |
| TLS ingress | Trusted certificate, HTTPS-only redirect, approved public hostname | NOT VERIFIED |
| Proxy trust | Restricted trusted proxy IPs; forged forwarding headers rejected; correct ASGI scheme/host | NOT VERIFIED |
| Cookie attributes | Secure, HttpOnly, SameSite and expiry checked in real browser | NOT VERIFIED on live HTTPS |
| Session revocation | Logout and password changes invalidate server-side sessions | Automated tests exist; live behavior NOT VERIFIED |
| Session expiry | JWT expiry and stored session expiry independently enforced | Automated tests exist; live behavior NOT VERIFIED |
| Account deactivation | Inactive accounts denied even with old cookies | Automated tests exist; live behavior NOT VERIFIED |
| Cross-site mutations | Missing/foreign Origin and Referer denied; same-origin actions allowed | Automated tests exist; proxy/browser behavior NOT VERIFIED |
| Classroom workflow | Lesson opening and progress submission succeed over real HTTPS | NOT VERIFIED |
| Owner & instructor | Role changes and approvals work only for authorized accounts | NOT VERIFIED on live HTTPS |
| MFA | Enrollment, challenge, recovery, and logout function over HTTPS | NOT VERIFIED on live HTTPS |
| HSTS | Applied only after TLS and subdomain scope are confirmed | NOT VERIFIED |
| Operational recovery | Backup/restore, incident response, and owner signoff | NOT VERIFIED |

## Acceptance procedure

1. Record the exact commit SHA, pull request, CI workflow run and test results.
2. Review the proxy trust boundary and verify HTTPS configuration in a **separate, authorized nonproduction environment** before considering any production change.
3. Use disposable test accounts and nonproduction data; never collect or copy secrets into the evidence package.
4. Record for each gate: date, environment, tester, test case, expected/actual result, and redacted evidence link.
5. Mark a gate PASS only after reproducible verification; otherwise mark FAIL or BLOCKED.
6. Keep the pull request draft, do not merge or deploy, and do not change production settings until the owner explicitly approves the next release action.

## Decision

**Release gate: BLOCKED.** A passing CI run does not demonstrate production readiness. This record is not a launch authorization.

## Automated evidence snapshot — CI run #382

- Commit: `fd70aca494399997c6ec68fe7174bd6d6df7146f`
- Workflow: [CrownPath CI #382](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/38184950490)
- Application job: **PASS**
- Owner-access job: **PASS**
- Migration job: **PASS**
- Evidence type: GitHub Actions job conclusions. This is **not** a production browser or reverse-proxy test.
- Remaining gate: **BLOCKED** pending authorized nonproduction HTTPS and proxy validation, browser security checks, and explicit owner release approval.
