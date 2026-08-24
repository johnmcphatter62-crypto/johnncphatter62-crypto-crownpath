from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from crownpath.db_config import database_url

URL = database_url()

connect_args = {}
if URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    URL,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True
)

class Base(DeclarativeBase):
    pass

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
