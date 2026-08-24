# CrownPath Production Activation Guide

CrownPath must remain in preview/staging until the real hosting environment, PostgreSQL database, secrets, HTTPS, backups, security verification, and authorized external services are configured.

## Required sequence
1. Configure production PostgreSQL and reviewed migrations.
2. Store application secrets in the deployment environment, never in GitHub.
3. Disable demo mode.
4. Verify security and backup/restore checks.
5. Configure authorized external providers and playback devices if enabled.
6. Verify login, MFA, authorization, auditing, Academy, digital content, regulatory architecture, inventory, avatar guidance, and health endpoints.
7. Record owner approval only after critical tests pass.
8. Monitor health, audit events, database, backups, errors, and provider status after launch.

Status: READY FOR DEPLOYMENT CONFIGURATION / NOT YET CLAIMED AS LIVE PRODUCTION.
