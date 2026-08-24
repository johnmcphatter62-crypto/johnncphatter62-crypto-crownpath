import os

REQUIRED_PRODUCTION_ENV_VARS = [
    "CROWNPATH_DATABASE_URL",
    "CROWNPATH_SECRET_KEY",
]

def validate_startup():
    env = os.getenv("CROWNPATH_ENV", "development").lower()

    if env != "production":
        return {
            "environment": env,
            "production_guard": "NOT_REQUIRED"
        }

    missing = [
        name for name in REQUIRED_PRODUCTION_ENV_VARS
        if not os.getenv(name)
    ]

    if missing:
        raise RuntimeError(
            "CrownPath production startup blocked. Missing: "
            + ", ".join(missing)
        )

    if os.getenv("CROWNPATH_DEMO_MODE", "true").lower() != "false":
        raise RuntimeError(
            "CrownPath production startup blocked because demo mode is enabled."
        )

    if os.getenv("CROWNPATH_OWNER_LAUNCH_APPROVED", "false").lower() != "true":
        raise RuntimeError(
            "CrownPath production startup blocked pending owner launch approval."
        )

    return {
        "environment": env,
        "production_guard": "PASSED"
    }
