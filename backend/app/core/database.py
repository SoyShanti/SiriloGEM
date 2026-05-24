from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from backend.app.core.config import settings
import logging

logger = logging.getLogger("spotigem.db")

engine = create_engine(settings.DATABASE_URL, echo=settings.APP_DEBUG)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


async def init_db():
    from backend.app.models import tables  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
