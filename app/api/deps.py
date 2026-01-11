from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import session_factory


async def get_db() -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
