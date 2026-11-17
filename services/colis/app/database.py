"""Connexion SQLAlchemy; PostgreSQL est obligatoire hors tests."""
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def _database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        # SQLite n'est utilise que si le developpeur le demande explicitement.
        url = os.getenv("TEST_DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL doit être définie dans l'environnement")
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


DATABASE_URL = _database_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
