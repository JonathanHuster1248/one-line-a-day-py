from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, delete, get, put
from litestar.di import NamedDependency
from litestar.exceptions import ClientException, PermissionDeniedException

from ..data.db import UserDb
from ..model import UserPublic
from ..schemas import to_public_user

UsersDb = NamedDependency[UserDb]


def _check_is_self(request: Request, user_id: UUID) -> None:
    if request.user.id != user_id:
        raise PermissionDeniedException(detail="Cannot modify another user's record")


class UserController(Controller):
    path = "/users"

    @get("/")
    async def list_users(self, users_db: UsersDb) -> list[UserPublic]:
        users = await users_db.list_users()
        return [to_public_user(user) for user in users]

    @get("/{user_id:uuid}")
    async def get_user_by_id(self, users_db: UsersDb, user_id: UUID) -> UserPublic:
        user = await users_db.get_user_by_id(user_id)
        return to_public_user(user)

    @get("/name/{user_name:str}")
    async def get_user_by_name(self, users_db: UsersDb, user_name: str) -> UserPublic:
        user = await users_db.get_user_by_name(user_name)
        return to_public_user(user)

    @put("/{user_id:uuid}")
    async def update_user(
        self,
        request: Request,
        users_db: UsersDb,
        user_id: UUID,
        name: str | None = None,
    ) -> UserPublic:
        _check_is_self(request, user_id)
        if name is None:
            raise ClientException(detail="No fields provided to update")

        user = await users_db.update_user(user_id, name=name)
        return to_public_user(user)

    @delete("/{user_id:uuid}")
    async def delete_user(
        self, request: Request, users_db: UsersDb, user_id: UUID
    ) -> None:
        _check_is_self(request, user_id)
        await users_db.delete_user(user_id)
