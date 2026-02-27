from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import config

async_engine = create_async_engine(str(config.DATABASE_URL))

async_session_factory = async_sessionmaker(
    bind=async_engine, autoflush=False, autocommit=False
)


class Base(DeclarativeBase):
    pass
