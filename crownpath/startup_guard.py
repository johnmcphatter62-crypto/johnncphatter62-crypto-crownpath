import os

REQUIRED_PRODUCTION_ENV_VARS = [
    "CROWNPATH_DATABASE_URL",
    "CROWNPATH_SECRET_KEY",
]

REQUIRED_PRODUCTION_FLAGS = {
    "CROWNPATH_DEMO_MODE": "false",
    "CROWNPATH_BACKUP_RESTORE_VERIFIED": "true",
    "CROWNPATH_SECURITY_TESTS_VERIFIED": "true",
    "CROWNPATH_OWNER_LAUNCH_APPROVED": "true",
}


def validate_startup():
    env = os.getenv("CROWNPATH_ENV", "development").lower()

    if env != "production":
        return {
            "environment": env,
            "production_guard": "NOT_REQUIRED",
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

    invalid_flags = []
    for name, expected in REQUIRED_PRODUCTION_FLAGS.items():
        actual = os.getenv(name, "").lower()
        if actual != expected:
            invalid_flags.append(f"{name} must be {expected}")

    if invalid_flags:
        raise RuntimeError(
            "CrownPath production startup blocked. "
            + "; ".join(invalid_flags)
        )

    return {
        "environment": env,
        "production_guard": "PASSED",
    }
