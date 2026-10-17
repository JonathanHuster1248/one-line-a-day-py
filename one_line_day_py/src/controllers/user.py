from __future__ import annotations

from typing import Optional
from uuid import UUID

from litestar import Controller, delete, get, put

from .. import dependencies
from ..model import UserPublic
from ..schemas import to_public_user


class UserController(Controller):
    path = "/users"

    @get("/")
    async def list_users(self) -> list[UserPublic]:
        users = await dependencies.users_db.list_users()
        return [to_public_user(user) for user in users]

    @get("/{user_id:uuid}")
    async def get_user_by_id(self, user_id: UUID) -> UserPublic:
        user = await dependencies.users_db.get_user_by_id(user_id)
        return to_public_user(user)

    @get("/name/{user_name:str}")
    async def get_user_by_name(self, user_name: str) -> UserPublic:
        user = await dependencies.users_db.get_user_by_name(user_name)
        return to_public_user(user)

    @put("/{user_id:uuid}")
    async def update_user(
        self, user_id: UUID, name: Optional[str] = None
    ) -> UserPublic:
        user = await dependencies.users_db.update_user(user_id, name=name)
        return to_public_user(user)

    @delete("/{user_id:uuid}")
    async def delete_user(self, user_id: UUID) -> None:
        await dependencies.users_db.delete_user(user_id)
