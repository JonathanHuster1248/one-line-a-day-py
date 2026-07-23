from __future__ import annotations

from uuid import UUID

from litestar import Controller, get, post, put, delete
from litestar.response import File

from datetime import date
from typing import Optional, Iterable

from .model import JournalEntry, User
from .settings import settings, DbType
from .data.json_back import JsonDb
from .data.sql_back import UserSqlDb, JournalSqlDb

backend_map = {
    DbType.JSON: JsonDb,
    DbType.SQL: {
        "users": UserSqlDb,
        "journals":JournalSqlDb,
    },
}
db = backend_map[settings.db_type]

users_db = db["users"](settings.db_path)
journals_db = db["journals"](settings.db_path)


class EntryController(Controller):
    path = "/"

    @get("/")
    async def hello_world(self) -> dict:
        return {"hello": "world"}

    @get("/favicon.ico")
    async def get_favicon(self) -> File:
        return File(path="one_line_day_py/static/favicon.ico")


class UserController(Controller):
    path = "/users"

    @post("/")
    async def create_user(self, name: str) -> User:
        user = User(name)
        await db.add_user(user)
        return user

    @get("/")
    async def list_users(self) -> list[User]:
        users = await db.list_users()
        return users

    @get("/{user_id:uuid}")
    async def get_user_by_id(self, user_id: UUID) -> User:
        user = await db.get_user_by_id(user_id)
        return user

    @get("/{user_name:str}")
    async def get_user_id_by_name(self, user_name: str) -> UUID:
        user_id = await db.get_user_id_by_name(user_name)
        return user_id

    @put("/{user_id:uuid}")
    async def update_user(self, user_id: UUID, name: Optional[str] = None) -> User:
        existing_user = self.get_user_by_id(user_id)

        name = name or existing_user.name

        updated_user = User(name=name)
        user = await db.update_user(user_id, updated_user)
        return user

    @delete("/{user_id:uuid}")
    async def delete_user(self, user_id: UUID) -> None:
        await db.delete_user(user_id)


# TODO: Use Litestar's dependency injection for this instead of just relying on db being made at the top of the file
class JournalController(Controller):
    path = "/journals"

    @post("/")
    async def create_journal(
        self, user_id: UUID, date: date, message: str, photos: Iterable[str] = ()
    ) -> JournalEntry:
        journal_entry = JournalEntry(date=date, message=message, photos=list(photos))
        entry = await db.add_journal(user_id, journal_entry)
        return entry

    @get("/")
    async def list_journals(self) -> list[JournalEntry]:
        entries = await db.list_journals()
        return entries

    @get("/{entry_id:uuid}")
    async def get_journal(self, entry_id: UUID) -> JournalEntry:
        entry = await db.get_journal(entry_id)
        return entry

    @get("/{entry_id:uuid}/author")
    async def get_journal_author(self, entry_id: UUID) -> UUID:
        author_id = await db.get_journal_author(entry_id)
        return author_id

    @put("/{entry_id:uuid}")
    async def update_journal(
        self,
        entry_id: UUID,
        user_id: Optional[UUID] = None,
        input_date: Optional[date] = None,
        message: Optional[str] = None,
        photos: Iterable[str] = (),
    ) -> JournalEntry:
        # TODO: identify if I want to have photos overwrite or append. Defaulting to overwrite for now
        existing_entry = self.get_journal(entry_id)
        existing_author = self.get_journal_author(entry_id)

        author_id = user_id or existing_author
        input_date = input_date or existing_entry.date
        message = message or existing_entry.message
        photos = photos or existing_entry.photos

        updated_data = JournalEntry(date=input_date, message=message, photos=photos)

        entry = await db.update_journal(entry_id, author_id, updated_data)
        return entry

    @delete("/{entry_id:uuid}")
    async def delete_journal(self, entry_id: UUID) -> None:
        await db.delete(entry_id)
