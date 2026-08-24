import shutil
from datetime import datetime, timezone
from pathlib import Path

def backup_sqlite():
    source = Path(__file__).resolve().parent.parent / "crownpath_demo.db"
    if not source.exists():
        return None
    backup_dir = Path(__file__).resolve().parent.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    target = backup_dir / f"crownpath_demo_{stamp}.db"
    shutil.copy2(source, target)
    return str(target)

def production_backup_note():
    return ("For PostgreSQL production, use managed snapshots and/or pg_dump, "
            "plus tested restore procedures. Do not rely on copying database files.")
