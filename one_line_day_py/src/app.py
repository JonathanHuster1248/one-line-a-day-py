from __future__ import annotations

from uuid import UUID

from litestar import Controller, get, post, put, delete
from litestar.response import File, Redirect

from datetime import date
from typing import Optional

from .model import JournalEntry, User
from .settings import settings
from .data.sql_back import UserSqlDb, JournalSqlDb

users_db = UserSqlDb(settings.db_path)
journals_db = JournalSqlDb(settings.db_path)


class EntryController(Controller):
    path = "/"

    @get("/")
    async def entry(self) -> Redirect:
        return Redirect("/schema/swagger/")

    @get("/hello_world")
    async def hello_world(self) -> str:
        return "Hello World!"

    @get("/favicon.ico")
    async def get_favicon(self) -> File:
        return File(path="one_line_day_py/static/favicon.ico")


class UserController(Controller):
    path = "/users"

    @post("/")
    async def create_user(self, name: str) -> User:  # Maybe return the user-id instead?
        user = User(name=name)
        await users_db.add_user(user)
        return user

    @get("/")
    async def list_users(self) -> list[User]:
        users = await users_db.list_users()
        return users

    @get("/{user_id:uuid}")
    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await users_db.get_user_by_id(user_id)
        return user

    @get("/name/{user_name:str}")
    async def get_user_by_name(self, user_name: str) -> User:
        user_id = await users_db.get_user_id_by_name(user_name)
        return user_id

    @put("/{user_id:uuid}")
    async def update_user(self, user_id: UUID, name: Optional[str] = None) -> User:
        existing_user = await users_db.get_user_by_id(user_id)

        name = name or existing_user.name

        updated_user = User(id=user_id, name=name)
        user = await users_db.update_user(user_id, updated_user)
        return user

    @delete("/{user_id:uuid}")
    async def delete_user(self, user_id: UUID) -> None:
        await users_db.delete_user(user_id)


# TODO: Use Litestar's dependency injection for this instead of just relying on db being made at the top of the file
class JournalController(Controller):
    path = "/journals"

    @post("/")
    async def create_entry(
        self, author_id: UUID, date: date, message: str
    ) -> JournalEntry:
        entry = JournalEntry(author_id=author_id, date=date, message=message)
        uploaded_entry = await journals_db.add_entry(entry)
        return uploaded_entry

    @get("/")
    async def list_entries(self) -> list[JournalEntry]:
        entries = await journals_db.list_entries()
        return entries

    @get("/{entry_id:uuid}")
    async def get_entry(self, entry_id: UUID) -> JournalEntry:
        entry = await journals_db.get_entry(entry_id)
        return entry

    @get("/{entry_id:uuid}/author")
    async def get_entry_author(self, entry_id: UUID) -> UUID:
        author_id = await journals_db.get_entry_author(entry_id)
        return author_id

    @put("/{entry_id:uuid}")
    async def update_entry(
        self,
        entry_id: UUID,
        author_id: Optional[UUID] = None,
        input_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> JournalEntry:
        existing_entry = await journals_db.get_entry(entry_id)

        author_id = author_id or existing_entry.author_id
        input_date = input_date or existing_entry.date
        message = message or existing_entry.message

        updated_entry = JournalEntry(
            id=entry_id,
            author_id=author_id,
            date=input_date,
            message=message,
        )
        await journals_db.update_entry(updated_entry)

        return updated_entry

    @delete("/{entry_id:uuid}")
    async def delete_entry(self, entry_id: UUID) -> None:
        await journals_db.delete_entry(entry_id)
