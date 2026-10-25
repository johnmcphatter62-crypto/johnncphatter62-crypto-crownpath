# CrownPath — Payment Integrity and Learner Privacy Review Gate

Status: SOURCE-REVIEW CHECKLIST ONLY. No payment processor account, production payment, customer data, or live credentials accessed.

## Evidence from current source review
- `crownpath/main.py` includes authenticated learner self-export and Owner-management routes.
- The inspected main application file did not establish a complete payment checkout, webhook validation, payout ownership, or refund/reconciliation workflow.
- This is **not** proof that no payment integration exists elsewhere in the repository or in connected services. Full repository and provider review remains OPEN.
- The learner self-export has synthetic PostgreSQL concurrency evidence from CI #539; that evidence does not cover payment records or the production privacy posture.

## Payment release gates — OPEN
| Control | Required evidence |
| --- | --- |
| Provider ownership | Authorized Owner controls the verified payment processor organization, administrative roles, and recovery methods |
| Payout protection | Bank/payout destination verified out-of-band; dual approval and alerts for any change, where supported |
| Hosted checkout | Checkout initiated server-side; prices and product IDs derived from trusted catalog, not browser-supplied totals |
| Webhook authenticity | Verify provider signature over the raw request body, enforce replay protection and idempotency, reject invalid events |
| Enrollment fulfillment | Grant course access only after a trusted server-side confirmation of settled or accepted payment status |
| Refunds and disputes | Document authorization, reconciliation, and reversal of entitlements where required |
| Redirect safety | Allowlist approved payment/return origins; do not trust arbitrary return URLs or client-provided redirect targets |
| Secrets and logging | No payment secrets, full card data, access tokens, or sensitive payloads in source control or audit logs |
| Reconciliation | Match processor events, internal orders, enrollment entitlements, refunds, and payouts with an auditable exception process |
| Independent verification | Synthetic negative tests for forged webhooks, duplicate events, altered prices, redirected payouts, and failure paths |

## Learner privacy gates — OPEN
- Confirm privacy notice, lawful processing basis, data inventory, retention schedule, and deletion/request procedures.
- Review role-based access and cross-learner isolation across all API endpoints, not just self-export.
- Verify audit records contain metadata only and do not expose credentials, learner content, or unnecessary personal data.
- Establish procedures for support access, breach escalation, and third-party processor/data-processing agreements.

## Next safe engineering steps
1. Identify all payment-related source files, configuration names, and routes **without reading any secrets**.
2. Write a payment threat model and synthetic tests for whichever provider integration is actually present; do not invent one.
3. Document any absent integration as a release blocker rather than enabling checkout or collecting payments.
4. Require Owner MFA and independent review before any production payment configuration or payout change.

Related synthetic CI evidence: https://github.com/johnmcphatter62-crypto/johnncphatter62-crypto-crownpath/actions/runs/40176358041

PR #46 must remain draft. No production payment activation or deployment is authorized by this document.
