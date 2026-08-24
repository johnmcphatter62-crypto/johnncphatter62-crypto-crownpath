from sqlalchemy import text
from crownpath.db_engine import engine, Base, SessionLocal
import crownpath.models  # noqa: F401

def init_db():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as con:
        con.execute(text('''CREATE TABLE IF NOT EXISTS system_metadata (key VARCHAR(100) PRIMARY KEY, value TEXT NOT NULL)'''))

def session():
    return SessionLocal()
