import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _normalize_database_url(url: str) -> str:
    # Railway commonly provides postgresql:// URLs. SQLAlchemy interprets that
    # as the psycopg2 dialect by default, while CrownPath installs psycopg v3.
    # Force the modern psycopg driver explicitly.
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    return url


def database_url():
    env = os.getenv("CROWNPATH_ENV", "development").lower()

    explicit = os.getenv("CROWNPATH_DATABASE_URL")
    if explicit:
        return _normalize_database_url(explicit)

    if env == "production":
        raise RuntimeError(
            "CROWNPATH_DATABASE_URL must be set in production."
        )

    return f"sqlite:///{BASE_DIR / 'crownpath_demo.db'}"
