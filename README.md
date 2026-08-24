# CrownPath

CrownPath is a modular education, client-experience, authorization, audit, and business-operations application prepared for staged deployment.

## Current deployment status

- Source repository ready
- Vercel/FastAPI entrypoint included
- PostgreSQL-ready configuration included
- Production startup is guarded until required environment configuration is present
- External business services remain disabled until separately authorized and configured

## Security

No production credentials, API keys, database passwords, streaming passwords, or secrets belong in this repository. Use deployment environment variables and a secret manager for production values.

## Local development

1. `python -m venv .venv`
2. Activate the virtual environment
3. `pip install -r requirements.txt`
4. `uvicorn crownpath.main:app --reload`
5. Open `http://127.0.0.1:8000`

See `GITHUB_VERCEL_HANDOFF.md` and `PRODUCTION_ACTIVATION_GUIDE.md` for deployment preparation.
