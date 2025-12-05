from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import config

engine = create_engine(config.DATABASE_URL)

sessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db_s = sessionLocal()
    try:
        yield db_s
    finally:
        db_s.close()
