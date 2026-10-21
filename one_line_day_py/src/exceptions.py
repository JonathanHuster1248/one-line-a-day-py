from http import HTTPStatus

from litestar import Request, Response
from litestar.exceptions import HTTPException
from litestar.exceptions.responses import create_exception_response
from litestar.types import ExceptionHandlersMap
from sqlalchemy.exc import NoResultFound


class AttachmentLimitExceeded(Exception):
    """The entry already has the maximum number of attachments."""


class AttachmentTooLarge(Exception):
    """The uploaded file is over the per-file size limit."""


class UnsupportedAttachmentType(Exception):
    """The file is neither a supported image nor a PDF."""


class AttachmentProcessingError(Exception):
    """The file could not be decoded or converted."""


class StorageUnavailable(Exception):
    """The attachments directory could not be written to."""


class DuplicateEntryDate(Exception):
    """The user already has a journal entry on that date."""


def _handler(status_code: int, detail: str):
    def handle(request: Request, exc: Exception) -> Response:
        http_exc = HTTPException(detail=detail, status_code=status_code)
        return create_exception_response(request, http_exc)

    return handle


exception_handlers: ExceptionHandlersMap = {
    NoResultFound: _handler(HTTPStatus.NOT_FOUND, "Not Found"),
    AttachmentLimitExceeded: _handler(
        HTTPStatus.BAD_REQUEST, "An entry can have at most 5 attachments"
    ),
    AttachmentTooLarge: _handler(
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "File is too large"
    ),
    UnsupportedAttachmentType: _handler(
        HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Unsupported file type"
    ),
    AttachmentProcessingError: _handler(
        HTTPStatus.UNPROCESSABLE_ENTITY, "File could not be processed"
    ),
    StorageUnavailable: _handler(
        HTTPStatus.SERVICE_UNAVAILABLE, "Attachment storage is unavailable"
    ),
    DuplicateEntryDate: _handler(
        HTTPStatus.CONFLICT, "An entry already exists for that date"
    ),
}
