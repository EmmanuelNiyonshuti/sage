from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Security
from fastapi.exceptions import HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.user import User

from .crud import find_user_by_key
from .security import hash_api_key


async def get_db() -> AsyncGenerator[AsyncSession, None, None]:
    async with async_session_factory() as async_session:
        yield async_session


SessionDep = Annotated[AsyncSession, Depends(get_db)]


api_key_header = APIKeyHeader(name="API-Key")


async def get_current_user(
    db_session: SessionDep,
    api_key: str = Security(api_key_header),
) -> User:
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Please add your API Key in your request headers",
        )
    api_key_hash = hash_api_key(api_key)
    user = await find_user_by_key(api_key_hash, db_session)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
