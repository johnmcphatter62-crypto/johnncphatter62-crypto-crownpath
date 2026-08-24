# CrownPath Launch Readiness

## Production gates
- PostgreSQL configured and migration-tested
- production application secret stored securely
- HTTPS/TLS enabled
- demo functionality disabled
- owner/staff authorization regression-tested
- backup and restore test completed
- audit retention configured
- security headers verified
- rate limiting and CSRF controls reviewed where applicable
- dependency/security scan completed
- health monitoring and alerting configured
- authorized business audio/device connections configured if enabled
- owner explicitly approves production activation

CrownPath must not store a user's Pandora password. Production activation remains conditional on real infrastructure and verified external authorization.
