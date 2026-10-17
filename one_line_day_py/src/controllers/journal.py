from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID

from litestar import Controller, Request, delete, get, post, put
from litestar.exceptions import NotFoundException
from litestar.params import FromQuery

from .. import dependencies
from ..model import JournalEntry


async def _get_owned_entry(entry_id: UUID, author_id: UUID) -> JournalEntry:
    entry = await dependencies.journals_db.get_entry(entry_id)
    if entry.author_id != author_id:
        raise NotFoundException()
    return entry


# TODO: Use Litestar's dependency injection for this instead of just relying on db existing throughout. This extends to the other controllers as well
class JournalController(Controller):
    path = "/journals"

    @post("/")
    async def create_entry(
        self, request: Request, date: date, message: str
    ) -> JournalEntry:
        entry = JournalEntry(author_id=request.user.id, date=date, message=message)
        uploaded_entry = await dependencies.journals_db.add_entry(entry)
        return uploaded_entry

    @get("/")
    async def list_entries(
        self,
        request: Request,
        month: FromQuery[int | None] = None,
        day: FromQuery[int | None] = None,
        year: FromQuery[int | None] = None,
    ) -> list[JournalEntry]:
        entries = await dependencies.journals_db.list_entries(
            request.user.id, month, day, year
        )
        return entries

    @get("/{entry_id:uuid}")
    async def get_entry(self, request: Request, entry_id: UUID) -> JournalEntry:
        return await _get_owned_entry(entry_id, request.user.id)

    @get("/{entry_id:uuid}/author")
    async def get_entry_author(self, request: Request, entry_id: UUID) -> UUID:
        entry = await _get_owned_entry(entry_id, request.user.id)
        return entry.author_id

    @put("/{entry_id:uuid}")
    async def update_entry(
        self,
        request: Request,
        entry_id: UUID,
        input_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> JournalEntry:
        existing_entry = await _get_owned_entry(entry_id, request.user.id)

        input_date = input_date or existing_entry.date
        message = message or existing_entry.message

        updated_entry = JournalEntry(
            id=entry_id,
            author_id=existing_entry.author_id,
            date=input_date,
            message=message,
        )
        await dependencies.journals_db.update_entry(updated_entry)

        return updated_entry

    @delete("/{entry_id:uuid}")
    async def delete_entry(self, request: Request, entry_id: UUID) -> None:
        await _get_owned_entry(entry_id, request.user.id)
        await dependencies.journals_db.delete_entry(entry_id)
