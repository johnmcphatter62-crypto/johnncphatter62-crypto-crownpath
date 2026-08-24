from contextlib import contextmanager
from crownpath.db_engine import SessionLocal

@contextmanager
def transaction():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
