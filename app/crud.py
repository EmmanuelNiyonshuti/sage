from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import SessionDep
from app.models import Parcel


def find_parcel_by_id(parcel_id: str, db: SessionDep) -> Parcel:
    stmt = select(Parcel).where(Parcel.uid == parcel_id)
    parcel = db.execute(stmt).scalars().first()
    return parcel


def list_parcels(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    is_active: bool | None = None,
    crop_type: str | None = None,
    search: str | None = None,
) -> tuple[list[Parcel], int]:
    query = select(Parcel)
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
    total = db.execute(count_query).scalar() or 0
    query = query.order_by(Parcel.created_at.desc()).limit(limit).offset(offset)

    parcels = list(db.execute(query).scalars().all())

    return parcels, total
