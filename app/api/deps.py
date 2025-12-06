from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import db_session


def get_db() -> Generator[Session, None, None]:
    with db_session() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]
