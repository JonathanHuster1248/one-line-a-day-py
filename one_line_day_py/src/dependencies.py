from __future__ import annotations

import logging
from uuid import UUID

from litestar.datastructures import State

from .controllers.journal import AttachmentLookup, EntryAttachments
from .data.attachment_storage import AttachmentStorage
from .data.db import AttachmentDb, JournalDb, UserDb
from .services.attachments import AttachmentService
from .settings import settings

logger = logging.getLogger(__name__)


def create_users_db() -> UserDb:
    return UserDb(settings.db_path)


def create_journals_db() -> JournalDb:
    return JournalDb(settings.db_path)


def provide_users_db(state: State) -> UserDb:
    return state.users_db


def provide_journals_db(state: State) -> JournalDb:
    return state.journals_db


def create_attachment_service(journals_db: JournalDb) -> AttachmentService:
    return AttachmentService(
        attachments_db=AttachmentDb(settings.db_path),
        storage=AttachmentStorage(settings.attachments_path),
        journals_db=journals_db,
    )


def provide_attachment_service(state: State) -> AttachmentService:
    return state.attachment_service


def provide_entry_attachments(state: State) -> EntryAttachments:
    return state.entry_attachments


class GuardedEntryAttachments:
    """`EntryAttachments` over `AttachmentService` that never raises.

    Attachments are an enhancement: a failure here must not take entries down,
    so errors are logged (class only) and reported as `available=False`.
    """

    def __init__(self, service: AttachmentService):
        self.service = service

    async def for_entries(
        self, user_id: UUID, entry_ids: list[UUID]
    ) -> AttachmentLookup:
        try:
            by_entry = await self.service.list_for_entries(user_id, entry_ids)
        except Exception as exc:  # noqa: BLE001 - must never raise (NFR-9)
            logger.error("Attachment lookup failed: %s", type(exc).__name__)
            return AttachmentLookup(by_entry={}, available=False)
        return AttachmentLookup(by_entry=by_entry, available=True)

    async def remove_entry_files(self, entry_id: UUID) -> None:
        try:
            await self.service.remove_entry_files(entry_id)
        except Exception as exc:  # noqa: BLE001 - must never raise (NFR-9)
            logger.error(
                "Attachment file removal failed: entry=%s error=%s",
                entry_id,
                type(exc).__name__,
            )
