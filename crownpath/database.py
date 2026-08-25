import sqlite3
from pathlib import Path

from sqlalchemy import text

from crownpath.db_engine import engine, Base, SessionLocal, URL
import crownpath.models  # noqa: F401


def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as con:
        con.execute(
            text(
                """CREATE TABLE IF NOT EXISTS system_metadata (
                key VARCHAR(100) PRIMARY KEY,
                value TEXT NOT NULL
                )"""
            )
        )


def session():
    return SessionLocal()


def connect():
    """Compatibility connection for legacy CrownPath modules.

    The legacy audit/auth/resource helpers still use sqlite-style SQL and `?`
    parameters. Keep that compatibility only for the development/preview SQLite
    database. Production PostgreSQL should use the SQLAlchemy repositories and
    transaction layer instead of this helper.
    """
    if not URL.startswith("sqlite:///"):
        raise RuntimeError(
            "Legacy connect() is SQLite-only. Migrate this caller to the "
            "SQLAlchemy repository/transaction layer before production."
        )

    db_path = Path(URL.removeprefix("sqlite:///"))
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con
