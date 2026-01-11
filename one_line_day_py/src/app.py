from __future__ import annotations

from uuid import UUID

from litestar import Controller, get, post, put, delete
from litestar.response import File
from litestar.params import Body

from datetime import date
from typing import Optional, Iterable

from .model import JournalCreate, JournalEntry, JournalUpdate
from .settings import settings, DbType
from .data.json_back import JsonDb
from .data.sql_back import SqlDb

db_map = {
    DbType.JSON: JsonDb,
    DbType.SQL: SqlDb,
}
db_class = db_map[settings.db_type]

class EntryController(Controller):
    path = "/"

    @get("/")
    async def hello_world(self) -> dict:
        return {"hello":"world"}
    
    @get("/favicon.ico")
    async def get_favicon(self) -> File:
        return File(path="one_line_day_py/static/favicon.ico")


# TODO: Use Litestar's dependency injection for this instead
class JournalController(Controller):
    path = "/journals"

    # CREATE
    @post("/")
    async def create_journal(self, date: date, message: str, photos: Iterable[str] = ()) -> JournalEntry:
        data = JournalCreate(date=date, message=message, photos=list(photos))
        entry = await db_class.insert(data)
        return entry

    # READ ALL
    @get("/")
    async def list_journals(self) -> list[JournalEntry]:
        entries = await db_class.list()
        return entries

    # READ ONE
    @get("/{entry_id:uuid}")
    async def get_journal(self, entry_id: UUID) -> JournalEntry:
        entry = await db_class.get(entry_id)
        return entry

    # UPDATE
    @put("/{entry_id:uuid}")
    async def update_journal(
        self, entry_id: UUID, date: Optional[date] = None, message: Optional[str] = None, photos: Iterable[str] = ()
    ) -> JournalEntry:
        # TODO: identify if I want to have photos overwrite or append. Defaulting to overwrite for now
        updated_data = JournalUpdate(date=date, message=message, photos=photos)
        entry = await db_class.update(entry_id, updated_data)
        return entry

    # DELETE
    @delete("/{entry_id:uuid}")
    async def delete_journal(self, entry_id: UUID) -> None:
        await db_class.delete(entry_id)


