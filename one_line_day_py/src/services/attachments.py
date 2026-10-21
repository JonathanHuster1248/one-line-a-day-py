import asyncio
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.exc import NoResultFound

from ..data.attachment_storage import TRASH_DIR, AttachmentStorage, Variant
from ..data.db import AttachmentDb, JournalDb
from ..exceptions import (
    AttachmentProcessingError,
    AttachmentTooLarge,
    UnsupportedAttachmentType,
)
from ..images import process_image
from ..model import Attachment, AttachmentKind, AttachmentPublic

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 15 * 1024 * 1024  # keep in sync with frontend/src/config.ts

PDF_CONTENT_TYPE = "application/pdf"
IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
    }
)
_STORED_IMAGE_CONTENT_TYPE = "image/webp"
_MAX_FILENAME_LENGTH = 255


@dataclass(frozen=True)
class OpenedAttachment:
    path: Path
    content_type: str
    filename: str


class AttachmentService:
    """The one place that knows how attachments work.

    `journals_db` is read-only here: it only confirms at upload that the target
    entry exists and belongs to the caller.
    """

    def __init__(
        self,
        attachments_db: AttachmentDb,
        storage: AttachmentStorage,
        journals_db: JournalDb,
    ):
        self.attachments_db = attachments_db
        self.storage = storage
        self.journals_db = journals_db

    async def _check_owned_entry(self, user_id: UUID, entry_id: UUID) -> None:
        entry = await self.journals_db.get_entry(entry_id)  # NoResultFound -> 404
        if entry.author_id != user_id:
            raise NoResultFound()

    async def add(
        self,
        user_id: UUID,
        entry_id: UUID,
        filename: str | None,
        content_type: str | None,
        data: bytes,
    ) -> AttachmentPublic:
        await self._check_owned_entry(user_id, entry_id)

        if len(data) > MAX_FILE_BYTES:
            raise AttachmentTooLarge()
        declared = (content_type or "").split(";")[0].strip().lower()
        is_pdf = declared == PDF_CONTENT_TYPE
        if not is_pdf and declared not in IMAGE_CONTENT_TYPES:
            raise UnsupportedAttachmentType()

        attachment_id = uuid4()
        files: dict[Variant, bytes]
        if is_pdf:
            if not data.startswith(b"%PDF-"):
                raise AttachmentProcessingError()
            files = {Variant.PDF: data}
            attachment = Attachment(
                id=attachment_id,
                entry_id=entry_id,
                author_id=user_id,
                kind=AttachmentKind.PDF,
                content_type=PDF_CONTENT_TYPE,
                size_bytes=len(data),
                has_thumbnail=False,
            )
        else:
            processed = await asyncio.to_thread(process_image, data)
            files = {Variant.THUMB: processed.thumb, Variant.DISPLAY: processed.display}
            attachment = Attachment(
                id=attachment_id,
                entry_id=entry_id,
                author_id=user_id,
                kind=AttachmentKind.IMAGE,
                content_type=_STORED_IMAGE_CONTENT_TYPE,
                size_bytes=len(processed.display),
                has_thumbnail=True,
                width=processed.width,
                height=processed.height,
                taken_at=processed.taken_at,
            )
        attachment.filename = (filename or "attachment")[:_MAX_FILENAME_LENGTH]
        attachment.original_content_type = declared
        attachment.content_hash = hashlib.sha256(data).hexdigest()

        try:
            for variant, content in files.items():
                await asyncio.to_thread(
                    self.storage.save, entry_id, attachment_id, variant, content
                )
            saved = await self.attachments_db.add_attachment(attachment)
        except Exception as exc:
            # A failed upload must leave neither files nor a row behind.
            try:
                self.storage.delete_attachment(entry_id, attachment_id)
            except OSError:
                pass  # best effort; the startup sweep covers leftovers
            logger.warning(
                "Attachment upload failed: entry=%s kind=%s content_type=%s size=%d error=%s",
                entry_id,
                attachment.kind,
                declared,
                len(data),
                type(exc).__name__,
            )
            raise

        logger.info(
            "Attachment stored: id=%s kind=%s content_type=%s size=%d",
            saved.id,
            saved.kind,
            saved.content_type,
            saved.size_bytes,
        )
        return AttachmentPublic.model_validate(saved)

    async def list_for_entry(
        self, user_id: UUID, entry_id: UUID
    ) -> list[AttachmentPublic]:
        # 404 for someone else's entry, like every other attachment route,
        # rather than an empty list.
        await self._check_owned_entry(user_id, entry_id)
        rows = await self.attachments_db.list_for_entry(entry_id, user_id)
        return [AttachmentPublic.model_validate(row) for row in rows]

    async def list_for_entries(
        self, user_id: UUID, entry_ids: list[UUID]
    ) -> dict[UUID, list[AttachmentPublic]]:
        by_entry = await self.attachments_db.list_for_entries(entry_ids, user_id)
        return {
            entry_id: [AttachmentPublic.model_validate(row) for row in rows]
            for entry_id, rows in by_entry.items()
        }

    async def delete(self, user_id: UUID, entry_id: UUID, attachment_id: UUID) -> None:
        attachment = await self.attachments_db.get_scoped(
            attachment_id, entry_id, user_id
        )
        if attachment is None:
            raise NoResultFound()
        await self.attachments_db.delete(attachment_id)
        self.storage.delete_attachment(entry_id, attachment_id)

    async def open(
        self,
        user_id: UUID,
        entry_id: UUID,
        attachment_id: UUID,
        *,
        thumbnail: bool = False,
    ) -> OpenedAttachment:
        """Resolve what to serve; any missing, foreign or file-less case is NoResultFound."""
        attachment = await self.attachments_db.get_scoped(
            attachment_id, entry_id, user_id
        )
        if attachment is None:
            raise NoResultFound()
        if thumbnail:
            if not attachment.has_thumbnail:
                raise NoResultFound()
            variant, content_type = Variant.THUMB, _STORED_IMAGE_CONTENT_TYPE
        elif attachment.kind == AttachmentKind.PDF:
            variant, content_type = Variant.PDF, attachment.content_type
        else:
            variant, content_type = Variant.DISPLAY, attachment.content_type
        path = self.storage.path_for(entry_id, attachment_id, variant)
        if path is None:
            raise NoResultFound()
        return OpenedAttachment(
            path=path, content_type=content_type, filename=attachment.filename
        )

    async def remove_entry_files(self, entry_id: UUID) -> None:
        self.storage.delete_entry(entry_id)

    async def sweep_orphans(self) -> None:
        """Startup backstop: move directories whose entry no longer exists to the trash.

        Moved rather than deleted, so pointing the app at the wrong or an empty
        database can't destroy every attachment. Never raises, so it can't block
        startup.
        """
        try:
            on_disk = self.storage.entry_dirs()
            alive = await self.attachments_db.existing_entry_ids(on_disk)
            orphans = [entry_id for entry_id in on_disk if entry_id not in alive]
            for entry_id in orphans:
                self.storage.trash_entry(entry_id)
            if orphans:
                logger.warning(
                    "Moved %d orphaned attachment directories to %s",
                    len(orphans),
                    self.storage.root / TRASH_DIR,
                )
        except Exception as exc:  # noqa: BLE001 - must never raise (NFR-9)
            logger.error("Attachment orphan sweep failed: %s", type(exc).__name__)
