import os
from typing import Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

os.environ["ENV_STATE"] = "test"
from alembic import command
from alembic.config import Config
from app.api.deps import get_db
from app.core.database import Base, engine
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def db():
    Base.metadata.drop_all(bind=engine)
    with engine.connect() as conn:  # drop alembic_version table so migrations run fresh
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        conn.commit()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    command.upgrade(alembic_cfg, "head")
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(db) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(
        bind=connection, autocommit=False, autoflush=False, expire_on_commit=False
    )
    session = session_factory()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
async def async_client(db_session) -> Generator[TestClient, None, None]:
    def overrides_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = overrides_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c
    app.dependency_overrides.clear()
