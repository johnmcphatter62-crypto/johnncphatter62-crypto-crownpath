from sqlalchemy import text
from crownpath.db_engine import engine

def ensure_migration_table():
    with engine.begin() as con:
        con.execute(text(
            '''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id VARCHAR(120) PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            '''
        ))

def applied_migrations():
    ensure_migration_table()
    with engine.begin() as con:
        rows = con.execute(
            text("SELECT migration_id, applied_at FROM schema_migrations ORDER BY applied_at")
        ).mappings().all()
        return [dict(row) for row in rows]
