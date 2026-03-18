import pytest
from httpx import AsyncClient

from app.api.security import hash_api_key


@pytest.mark.anyio
def test_hash_api_key():
    api_key = "hello"
    api_key_hash = hash_api_key(api_key)
    assert len(api_key_hash) == 64
    assert all(c in "0123456789abcdef" for c in api_key_hash)


@pytest.mark.anyio
async def test_add_new_user(async_client: AsyncClient):
    response = await async_client.post(
        "/api/v1/register", json={"email": "john@gmail.com"}
    )
    assert response.status_code == 201
    assert "api_key" in response.json()
