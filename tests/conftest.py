import os
from typing import Generator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

os.environ["ENV_STATE"] = (
    "test"  # switch the application to use tests environnment variables before we import anything from the app
)
from alembic.config import Config

from alembic import command
from app.api.deps import get_db
from app.core.config import config
from app.core.database import Base
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def db():
    sync_engine = create_engine(
        str(config.DATABASE_URL).replace("postgresql+asyncpg", "postgresql")
    )  # we need to create a synchronous engine for setup/teardown in tests because alembic is running synchronously
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option(
        "sqlalchemy.url", sync_engine.url.render_as_string(hide_password=False)
    )
    command.upgrade(alembic_cfg, "head")
    yield
    Base.metadata.drop_all(bind=sync_engine)
    with (
        sync_engine.connect() as conn
    ):  # drop alembic_version table so migrations run fresh
        conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        conn.commit()


@pytest.fixture()
async def db_session(db) -> Generator[AsyncSession, None, None]:
    """
    we need to use a separate session for tests with a separate async engine.
    setup and teardown fixture(db) uses a sync engine
    """
    async_engine = create_async_engine(str(config.DATABASE_URL))

    # We open a connection and start our own transaction on it.
    # We then bind the session to that connection instead of the engine.
    # Because the session is joining a connection that already has an open
    # transaction, it becomes a guest meaning it can read and write, but its
    # commit() calls do not issue a real COMMIT to the database.
    # This keeps our outer transaction open so that at the end of each test
    # we can call connection.rollback(), which undoes everything the test did
    # and leaves the database clean for the next test.
    async with async_engine.connect() as connection:
        await connection.begin()

        AsyncTestSessionLocal = async_sessionmaker(
            bind=connection,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        async with AsyncTestSessionLocal() as session:
            yield session
        await connection.rollback()


@pytest.fixture()
async def async_client(db_session: AsyncSession) -> Generator[TestClient, None, None]:
    async def _overrides_get_db():
        yield db_session

    app.dependency_overrides[get_db] = (
        _overrides_get_db  # we need to override the application get_db dependency to let tests use their own session
    )
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
async def registered_user_api_key(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/register", json={"email": "john@gmail.com"}
    )
    return response.json()["api_key"]
