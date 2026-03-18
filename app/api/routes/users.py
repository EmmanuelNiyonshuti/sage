from fastapi import APIRouter
from fastapi.exceptions import HTTPException

from app.api.crud import add_new_user, find_user_by_email
from app.api.deps import SessionDep
from app.api.security import generate_api_key
from app.models.schemas import UserIn, UserOut

router = APIRouter(tags=["User"])


@router.post("/register", status_code=201)
async def user_register(user_data: UserIn, db_session: SessionDep):
    user = await find_user_by_email(user_data.email, db_session)
    if user:
        raise HTTPException(
            status_code=400, detail="User with this email already exists"
        )
    # email verification is not currently enforced
    api_key = generate_api_key()
    user_data.api_key = api_key
    new_user = await add_new_user(user_data, db_session)

    return UserOut(uid=new_user.uid, email=new_user.email, api_key=api_key)
