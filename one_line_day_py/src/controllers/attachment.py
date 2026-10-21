from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from litestar import Controller, Request, delete, get, post
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency
from litestar.enums import RequestEncodingType
from litestar.params import Body, FromQuery
from litestar.response import File

from ..model import AttachmentPublic
from ..services.attachments import AttachmentService, OpenedAttachment

AttachmentServiceDep = NamedDependency[AttachmentService]

# Leaves headroom over the 15 MB per-file limit for multipart framing, so an
# oversized file reaches the service and gets its 413 from there.
MAX_UPLOAD_BODY_BYTES = 16 * 1024 * 1024

# Content under an attachment ID never changes; `private` keeps shared caches out.
_SERVE_HEADERS = {
    "Cache-Control": "private, max-age=31536000, immutable",
    "X-Content-Type-Options": "nosniff",
}


@dataclass
class AttachmentUpload:
    file: UploadFile


def _serve(opened: OpenedAttachment, *, download: bool = False) -> File:
    # Litestar emits the filename RFC 5987-encoded, so it can't inject headers.
    return File(
        path=opened.path,
        media_type=opened.content_type,
        filename=opened.filename,
        content_disposition_type="attachment" if download else "inline",
        headers=_SERVE_HEADERS,
    )


class AttachmentController(Controller):
    """Thin HTTP adapter over `AttachmentService`; holds no rules and builds no paths."""

    path = "/journals/{entry_id:uuid}/attachments"

    @post("/", request_max_body_size=MAX_UPLOAD_BODY_BYTES)
    async def upload_attachment(
        self,
        request: Request,
        attachment_service: AttachmentServiceDep,
        entry_id: UUID,
        data: Annotated[
            AttachmentUpload, Body(media_type=RequestEncodingType.MULTI_PART)
        ],
    ) -> AttachmentPublic:
        upload = data.file
        content = await upload.read()
        return await attachment_service.add(
            request.user.id, entry_id, upload.filename, upload.content_type, content
        )

    @get("/")
    async def list_attachments(
        self,
        request: Request,
        attachment_service: AttachmentServiceDep,
        entry_id: UUID,
    ) -> list[AttachmentPublic]:
        return await attachment_service.list_for_entry(request.user.id, entry_id)

    @get("/{attachment_id:uuid}/thumbnail")
    async def get_thumbnail(
        self,
        request: Request,
        attachment_service: AttachmentServiceDep,
        entry_id: UUID,
        attachment_id: UUID,
    ) -> File:
        opened = await attachment_service.open(
            request.user.id, entry_id, attachment_id, thumbnail=True
        )
        return _serve(opened)

    @get("/{attachment_id:uuid}/content")
    async def get_content(
        self,
        request: Request,
        attachment_service: AttachmentServiceDep,
        entry_id: UUID,
        attachment_id: UUID,
        download: FromQuery[bool] = False,
    ) -> File:
        opened = await attachment_service.open(request.user.id, entry_id, attachment_id)
        return _serve(opened, download=download)

    @delete("/{attachment_id:uuid}")
    async def delete_attachment(
        self,
        request: Request,
        attachment_service: AttachmentServiceDep,
        entry_id: UUID,
        attachment_id: UUID,
    ) -> None:
        await attachment_service.delete(request.user.id, entry_id, attachment_id)
