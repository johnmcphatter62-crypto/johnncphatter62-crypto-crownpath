import os

def production_readiness():
    env = os.getenv("CROWNPATH_ENV", "development").lower()
    checks = {
        "production_environment": env == "production",
        "database_url_configured": bool(os.getenv("CROWNPATH_DATABASE_URL")),
        "application_secret_configured": bool(os.getenv("CROWNPATH_SECRET_KEY")),
        "pandora_business_configured": bool(os.getenv("CROWNPATH_PANDORA_BUSINESS_REFERENCE")),
        "playback_provider_configured": bool(os.getenv("CROWNPATH_PLAYBACK_PROVIDER")),
    }
    return {
        "environment": env,
        "checks": checks,
        "ready": all(checks.values()) if env == "production" else False,
    }
