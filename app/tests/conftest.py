"""fixtures for sharing data with multiple tests file

sharing fixtures to share data with multiple tests.
"""

import os
from typing import AsyncGenerator, Generator

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

os.environ["ENV_STATE"] = "test"

from app.main import app


@pytest.fixture(scope="session")  # runs once for entire test session, scope="session"
def anyio_backend():
    return "asyncio"


@pytest.fixture()
def client() -> Generator:
    yield TestClient(app)


@pytest.fixture()
async def async_client(client) -> AsyncGenerator:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url=client.base_url
    ) as c:
        yield c
