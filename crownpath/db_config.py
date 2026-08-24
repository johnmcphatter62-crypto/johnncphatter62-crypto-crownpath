import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def database_url():
    env = os.getenv("CROWNPATH_ENV", "development").lower()

    explicit = os.getenv("CROWNPATH_DATABASE_URL")
    if explicit:
        return explicit

    if env == "production":
        raise RuntimeError(
            "CROWNPATH_DATABASE_URL must be set in production."
        )

    return f"sqlite:///{BASE_DIR / 'crownpath_demo.db'}"
