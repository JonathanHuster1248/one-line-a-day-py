from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from litestar import Controller, Request, delete, get, post, put
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException
from litestar.params import FromQuery

from ..data.db import JournalDb
from ..model import JournalEntry

JournalsDb = NamedDependency[JournalDb]


async def _get_owned_entry(
    journals_db: JournalDb, entry_id: UUID, author_id: UUID
) -> JournalEntry:
    entry = await journals_db.get_entry(entry_id)
    if entry.author_id != author_id:
        raise NotFoundException()
    return entry


class JournalController(Controller):
    path = "/journals"

    @post("/")
    async def create_entry(
        self, request: Request, journals_db: JournalsDb, date: date, message: str
    ) -> JournalEntry:
        entry = JournalEntry(author_id=request.user.id, date=date, message=message)
        uploaded_entry = await journals_db.add_entry(entry)
        return uploaded_entry

    @get("/")
    async def list_entries(
        self,
        request: Request,
        journals_db: JournalsDb,
        month: FromQuery[int | None] = None,
        day: FromQuery[int | None] = None,
        year: FromQuery[int | None] = None,
    ) -> list[JournalEntry]:
        entries = await journals_db.list_entries(request.user.id, month, day, year)
        return entries

    @get("/{entry_id:uuid}")
    async def get_entry(
        self, request: Request, journals_db: JournalsDb, entry_id: UUID
    ) -> JournalEntry:
        return await _get_owned_entry(journals_db, entry_id, request.user.id)

    @get("/{entry_id:uuid}/author")
    async def get_entry_author(
        self, request: Request, journals_db: JournalsDb, entry_id: UUID
    ) -> UUID:
        entry = await _get_owned_entry(journals_db, entry_id, request.user.id)
        return entry.author_id

    @put("/{entry_id:uuid}")
    async def update_entry(
        self,
        request: Request,
        journals_db: JournalsDb,
        entry_id: UUID,
        input_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> JournalEntry:
        await _get_owned_entry(journals_db, entry_id, request.user.id)
        return await journals_db.update_entry(
            entry_id, date=input_date, message=message
        )

    @delete("/{entry_id:uuid}")
    async def delete_entry(
        self, request: Request, journals_db: JournalsDb, entry_id: UUID
    ) -> None:
        await _get_owned_entry(journals_db, entry_id, request.user.id)
        await journals_db.delete_entry(entry_id)
