from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import settings

import logging
logger = logging.getLogger(__name__)

db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if settings.is_production and db_url.startswith("sqlite"):
    logger.warning(
        "DATABASE_URL points to SQLite in production mode! "
        "Render filesystem is ephemeral; data will be reset on container restart. "
        "Ensure DATABASE_URL is linked to PostgreSQL."
    )

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
