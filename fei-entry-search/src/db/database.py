import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fei_entries.db"


def get_engine(db_path: str | Path | None = None):
    path = db_path or os.environ.get("FEI_DB_PATH", DEFAULT_DB_PATH)
    return create_engine(f"sqlite:///{path}", echo=False)


def get_session(db_path: str | Path | None = None) -> Session:
    engine = get_engine(db_path)
    return sessionmaker(bind=engine)()


def init_db(db_path: str | Path | None = None):
    """Create all tables if they don't exist."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
