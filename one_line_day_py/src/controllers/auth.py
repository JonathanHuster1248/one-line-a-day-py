from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, get, post
from litestar.connection import ASGIConnection
from litestar.di import NamedDependency
from litestar.exceptions import HTTPException, NotAuthorizedException
from litestar.status_codes import HTTP_409_CONFLICT
from sqlalchemy.exc import NoResultFound

from ..data.db import UserDb
from ..model import User, UserPublic
from ..schemas import LoginPayload, SignupPayload, to_public_user
from ..security import hash_password, verify_password

UsersDb = NamedDependency[UserDb]


async def retrieve_user_handler(
    session: dict, connection: ASGIConnection
) -> User | None:
    user_id = session.get("user_id")
    if user_id is None:
        return None
    users_db: UserDb = connection.app.state.users_db
    try:
        return await users_db.get_user_by_id(UUID(user_id))
    except NoResultFound:
        return None


class AuthController(Controller):
    path = "/auth"

    @post("/signup", exclude_from_auth=True)
    async def signup(
        self, request: Request, data: SignupPayload, users_db: UsersDb
    ) -> UserPublic:
        if await users_db.get_user_by_email(data.email) is not None:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail="Email already registered"
            )

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        await users_db.add_user(user)
        request.set_session({"user_id": str(user.id)})
        return to_public_user(user)

    @post("/login", exclude_from_auth=True)
    async def login(
        self, request: Request, data: LoginPayload, users_db: UsersDb
    ) -> UserPublic:
        user = await users_db.get_user_by_email(data.email)
        if user is None or not verify_password(data.password, user.hashed_password):
            raise NotAuthorizedException(detail="Invalid email or password")

        request.set_session({"user_id": str(user.id)})
        return to_public_user(user)

    @post("/logout", exclude_from_auth=True)
    async def logout(self, request: Request) -> None:
        request.clear_session()

    @get("/me")
    async def me(self, request: Request) -> UserPublic:
        return to_public_user(request.user)
