# CrownPath — Vercel Preview Access Preflight (Review Only)

**Status:** UNVERIFIED — blocks use of real pilot participant information. This document does not authorize deployment, invitations, or enrollment.

## Evidence observed on 2026-10-13

- Vercel deployment listing for project `project-kvb22` (`prj_YxrtBTcXBbgQ9YoNTx1mntpt5pDg`) shows two READY preview deployments with `target: null`:
  - PR #39 review branch `review/learner-progress-clean-20261012`, commit `9687abe6d8a01f636a5f5544d98be02639afc5c3`, deployment `dpl_HPgRLkFCk1rp38ybVvmfp77YD3cj`.
  - PR #40 review branch `review/private-pilot-checklist-20261013`, commit `0a92fb8b3c2da63cb1b9bf49ef72f7d283133d7e`, deployment `dpl_9eFrbmVibdTAeiBPuYVQCy84dW8g`.
- Deployment-list status READY means build availability, **not** authenticated/private access.
- Detailed project and deployment lookups returned not-found errors despite list visibility. Access protection settings therefore **could not be verified**; no conclusion about public exposure is justified.
- Vercel preview deployment is not evidence of an approved production release.

## Administrator-only, read-only verification

- [ ] Open Vercel project settings for the exact project ID and correct team; record inspector and review date.
- [ ] Inspect **Deployment Protection** for preview deployments and the applicable team/project overrides. Record the exact settings and whether authentication is required.
- [ ] Verify both preview URLs reject unauthenticated access to sensitive app pages and APIs. Use **synthetic accounts and data only**; do not bypass authentication or capture secrets.
- [ ] Confirm previews do not connect to production databases, storage, user identities, or payment services. Document evidence without copying credential values.
- [ ] Verify preview access is limited to authorized reviewers; check for shareable bypass links and revoke any unneeded links through normal owner-approved administration.
- [ ] Check preview logging and storage for retention of images, credentials, health details, and identifying information.
- [ ] Confirm photo upload/consent/deletion workflows separately before any participant photos are permitted.
- [ ] Record reviewer, date, findings, corrective actions, retest evidence, and owner acceptance in issue #41.

## Decision rule

**NO-GO for real participant data or invitations** until the security reviewer verifies isolation and protection, pilot safety/privacy reviewers sign off, and the owner explicitly authorizes the private pilot. A Vercel READY label or passing GitHub CI does not override this rule.

Related: [Private Pilot Readiness Checklist](CrownPath_Private_Pilot_Readiness_Checklist.md), [issue #41](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/issues/41), [PR #39](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/pull/39), [PR #40](https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/pull/40).
