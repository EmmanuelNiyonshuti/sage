from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.security import hash_api_key
from app.models import Parcel
from app.models.schemas import UserIn
from app.models.user import User


async def find_parcel_by_id(
    owner_id: str, parcel_id: str, db_session: AsyncSession
) -> Parcel:
    stmt = select(Parcel).where(Parcel.owner_id == owner_id, Parcel.uid == parcel_id)
    result = await db_session.execute(stmt)
    parcel = result.scalars().first()
    return parcel


async def list_parcels(
    db_session: AsyncSession,
    owner_id: str,
    *,
    limit: int = 50,
    offset: int = 0,
    is_active: bool | None = None,
    crop_type: str | None = None,
    search: str | None = None,
) -> tuple[list[Parcel], int]:
    query = select(Parcel).where(Parcel.owner_id == owner_id)
    count_query = select(func.count(Parcel.uid))
    filters = []

    if is_active is not None:
        filters.append(Parcel.is_active == is_active)

    if crop_type:
        filters.append(Parcel.crop_type == crop_type)

    if search:
        filters.append(Parcel.name.ilike(f"%{search}%"))

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)
    result = await db_session.execute(count_query)
    total = result.scalar() or 0
    query = query.order_by(Parcel.created_at.desc()).limit(limit).offset(offset)

    parcels = list((await db_session.execute(query)).scalars().all())

    return parcels, total


async def add_parcel_boundary(
    db_session: AsyncSession, parcel_data: dict[str, str]
) -> dict:
    """
    Add new parcel boundary to the database.
    Args:
        db_session_session: An Async database session
        parcel_data: a dictionary containing parcel boundary data
    Returns:
        A newly created parcel.
    """
    new_parcel = Parcel(**parcel_data)
    db_session.add(new_parcel)
    await db_session.commit()

    return new_parcel


async def find_user_by_email(email: str, db_session: AsyncSession) -> User:
    stmt = select(User).where(User.email == email)
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    return user


async def add_new_user(user_data: UserIn, db_session: AsyncSession) -> User:
    api_key_hash = hash_api_key(user_data.api_key)
    new_user = User(email=user_data.email, api_key_hash=api_key_hash)
    db_session.add(new_user)
    await db_session.commit()
    return new_user


async def find_user_by_key(key: str, db_session: AsyncSession) -> User:
    stmt = select(User).where(User.api_key_hash == key)
    result = await db_session.execute(stmt)
    user = result.scalars().first()
    return user
