# CrownPath reverse-proxy security checklist (review only)

CrownPath compares the browser's Origin (or Referer fallback) with the ASGI request URL for cookie-authenticated mutations. The application does **not** directly trust arbitrary `X-Forwarded-Host` or `X-Forwarded-Proto` headers.

Before any public launch:

1. Terminate TLS at the approved ingress and redirect HTTP to HTTPS.
2. Configure the ASGI server to trust forwarding headers **only** from known ingress proxy IP addresses. Do not use unrestricted forwarded-header trust on an internet-facing listener.
3. Preserve the public Host and scheme through the trusted proxy so `request.url` reflects the browser's actual origin. Reject unapproved Host values at the ingress.
4. Confirm `CROWNPATH_ENV=production`, `CROWNPATH_DEMO_MODE=false`, and `CROWNPATH_REQUIRE_HTTPS=true` are set before startup; do not mark security verification complete until tested.
5. Exercise browser login, logout, MFA, instructor approvals, and learner progress over the real HTTPS hostname. Confirm cross-site mutation attempts fail and same-site actions succeed.
6. Confirm session cookies carry `Secure`, `HttpOnly`, and `SameSite=Lax`; verify HSTS only on the intended HTTPS domain. Review `includeSubDomains` before enabling it on a shared parent domain.
7. Keep staging and production credentials, databases, domains, and deployment approvals separate.

**Status:** checklist only. No proxy, deployment, domain, or production configuration has been changed. Launch remains blocked pending authorized verification.
