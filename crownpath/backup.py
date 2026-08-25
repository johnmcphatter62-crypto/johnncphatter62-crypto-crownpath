import shutil
from datetime import datetime, timezone
from pathlib import Path

from crownpath.db_engine import URL


def is_sqlite_database():
    return URL.startswith("sqlite:///")


def is_postgres_database():
    return URL.startswith("postgresql://") or URL.startswith("postgresql+") or URL.startswith("postgres://")


def backup_sqlite():
    """Create a local SQLite backup for development only."""
    if not is_sqlite_database():
        raise RuntimeError(
            "backup_sqlite() is development-only. CrownPath production uses PostgreSQL; "
            "use Railway PITR/volume backups and a tested pg_dump restore workflow."
        )

    source = Path(URL.removeprefix("sqlite:///"))
    if not source.exists():
        return None

    backup_dir = Path(__file__).resolve().parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"crownpath_demo_{stamp}.db"
    shutil.copy2(source, target)
    return str(target)


def backup_strategy():
    if is_postgres_database():
        return {
            "database": "postgresql",
            "primary": "Railway Point-in-Time Recovery (PITR)",
            "secondary": "Railway volume backup and/or pg_dump logical backup",
            "restore_rule": "Restore into a separate database/service first, validate data, then cut over deliberately.",
            "verified": False,
        }

    return {
        "database": "sqlite",
        "primary": "local file copy",
        "secondary": None,
        "restore_rule": "Restore only while the application is stopped.",
        "verified": False,
    }


def production_backup_note():
    return (
        "CrownPath production PostgreSQL must use managed backups such as Railway PITR/volume backups "
        "and/or pg_dump, with a tested restore procedure. Never copy PostgreSQL data files as if they were SQLite."
    )
