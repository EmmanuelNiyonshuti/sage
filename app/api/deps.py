from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import async_session_factory


async def get_db() -> Generator[Session, None, None]:
    async with async_session_factory() as async_session:
        yield async_session


SessionDep = Annotated[Session, Depends(get_db)]
