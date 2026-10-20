from __future__ import annotations

from datetime import date
from typing import NamedTuple, Protocol, runtime_checkable
from uuid import UUID

from litestar import Controller, Request, delete, get, post, put
from litestar.di import NamedDependency
from litestar.exceptions import NotFoundException
from litestar.params import FromQuery

from ..data.db import JournalDb
from ..model import AttachmentPublic, JournalEntry
from ..schemas import JournalEntryPublic, to_public_entry

JournalsDb = NamedDependency[JournalDb]


class AttachmentLookup(NamedTuple):
    by_entry: dict[UUID, list[AttachmentPublic]]
    available: bool


@runtime_checkable
class EntryAttachments(Protocol):
    """All the journal side needs from attachments; implemented by a never-raising adapter."""

    async def for_entries(
        self, user_id: UUID, entry_ids: list[UUID]
    ) -> AttachmentLookup: ...

    async def remove_entry_files(self, entry_id: UUID) -> None: ...


EntryAttachmentsDep = NamedDependency[EntryAttachments]


async def _get_owned_entry(
    journals_db: JournalDb, entry_id: UUID, author_id: UUID
) -> JournalEntry:
    entry = await journals_db.get_entry(entry_id)
    if entry.author_id != author_id:
        raise NotFoundException()
    return entry


async def _with_attachments(
    entry_attachments: EntryAttachments, user_id: UUID, entries: list[JournalEntry]
) -> list[JournalEntryPublic]:
    """Embed attachment metadata, fetched for all entries in one call."""
    lookup = await entry_attachments.for_entries(user_id, [e.id for e in entries])
    return [
        to_public_entry(e, lookup.by_entry.get(e.id, []), lookup.available)
        for e in entries
    ]


class JournalController(Controller):
    path = "/journals"

    @post("/")
    async def create_entry(
        self, request: Request, journals_db: JournalsDb, date: date, message: str
    ) -> JournalEntryPublic:
        entry = JournalEntry(author_id=request.user.id, date=date, message=message)
        uploaded_entry = await journals_db.add_entry(entry)
        return to_public_entry(uploaded_entry, [])

    @get("/")
    async def list_entries(
        self,
        request: Request,
        journals_db: JournalsDb,
        entry_attachments: EntryAttachmentsDep,
        month: FromQuery[int | None] = None,
        day: FromQuery[int | None] = None,
        year: FromQuery[int | None] = None,
    ) -> list[JournalEntryPublic]:
        entries = await journals_db.list_entries(request.user.id, month, day, year)
        return await _with_attachments(entry_attachments, request.user.id, entries)

    @get("/{entry_id:uuid}")
    async def get_entry(
        self,
        request: Request,
        journals_db: JournalsDb,
        entry_attachments: EntryAttachmentsDep,
        entry_id: UUID,
    ) -> JournalEntryPublic:
        entry = await _get_owned_entry(journals_db, entry_id, request.user.id)
        [public] = await _with_attachments(entry_attachments, request.user.id, [entry])
        return public

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
        entry_attachments: EntryAttachmentsDep,
        entry_id: UUID,
        input_date: date | None = None,
        message: str | None = None,
    ) -> JournalEntryPublic:
        await _get_owned_entry(journals_db, entry_id, request.user.id)
        entry = await journals_db.update_entry(
            entry_id, date=input_date, message=message
        )
        [public] = await _with_attachments(entry_attachments, request.user.id, [entry])
        return public

    @delete("/{entry_id:uuid}")
    async def delete_entry(
        self,
        request: Request,
        journals_db: JournalsDb,
        entry_attachments: EntryAttachmentsDep,
        entry_id: UUID,
    ) -> None:
        await _get_owned_entry(journals_db, entry_id, request.user.id)
        # Attachment rows go with the entry via ON DELETE CASCADE; files are ours.
        await journals_db.delete_entry(entry_id)
        await entry_attachments.remove_entry_files(entry_id)
