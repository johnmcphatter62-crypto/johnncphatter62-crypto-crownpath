# CrownPath GitHub → Vercel Handoff

Recommended repository: this repository's `main` branch.

## Publish sequence
1. Keep secrets out of GitHub.
2. Import this repository into Vercel.
3. Create and verify a Preview deployment.
4. Configure Preview environment variables.
5. Configure Production environment variables.
6. Run reviewed PostgreSQL migrations.
7. Verify backup/recovery and security checks.
8. Promote to Production only after all release gates pass.

## Required production environment variables
CROWNPATH_ENV=production
CROWNPATH_DATABASE_URL=<PostgreSQL connection>
CROWNPATH_SECRET_KEY=<strong secret>
CROWNPATH_DEMO_MODE=false
CROWNPATH_BACKUP_RESTORE_VERIFIED=true
CROWNPATH_SECURITY_TESTS_VERIFIED=true
CROWNPATH_OWNER_LAUNCH_APPROVED=true

Do not commit secrets, passwords, API keys, payment credentials, or production database credentials to GitHub.
