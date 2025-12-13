from sqlalchemy import select

from app.api.deps import SessionDep
from app.models import Parcel


def find_parcel_by_id(parcel_id: str, db: SessionDep) -> Parcel:
    stmt = select(Parcel).where(Parcel.uid == parcel_id)
    parcel = db.execute(stmt).scalars().first()
    return parcel
