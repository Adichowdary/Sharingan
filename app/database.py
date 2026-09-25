"""
PhishGuard Database Setup (SQLite + SQLAlchemy)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables and perform lightweight schema migrations."""
    from app import models  # noqa: F401 — triggers table registration
    Base.metadata.create_all(bind=engine)

    # Lightweight migration check for new columns on SQLite
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE campaigns ADD COLUMN redirect_url TEXT DEFAULT ''"))
            conn.commit()
        except Exception:
            pass  # Column already exists
