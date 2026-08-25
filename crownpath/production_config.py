import os


def production_readiness():
    env = os.getenv("CROWNPATH_ENV", "development").lower()

    core_checks = {
        "production_environment": env == "production",
        "database_url_configured": bool(os.getenv("CROWNPATH_DATABASE_URL")),
        "application_secret_configured": bool(os.getenv("CROWNPATH_SECRET_KEY")),
    }

    audio_checks = {
        "pandora_business_configured": bool(os.getenv("CROWNPATH_PANDORA_BUSINESS_REFERENCE")),
        "playback_provider_configured": bool(os.getenv("CROWNPATH_PLAYBACK_PROVIDER")),
    }

    return {
        "environment": env,
        "checks": core_checks,
        "ready": all(core_checks.values()) if env == "production" else False,
        "optional_features": {
            "client_audio": {
                "checks": audio_checks,
                "ready": all(audio_checks.values()),
            }
        },
    }
