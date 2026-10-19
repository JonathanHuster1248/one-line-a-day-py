import pytest
from litestar import Litestar, get
from litestar.testing import TestClient

from one_line_day_py.src.exceptions import (
    AttachmentLimitExceeded,
    AttachmentProcessingError,
    AttachmentTooLarge,
    StorageUnavailable,
    UnsupportedAttachmentType,
    exception_handlers,
)


@pytest.mark.parametrize(
    ("exc_type", "status"),
    [
        (AttachmentLimitExceeded, 400),
        (AttachmentTooLarge, 413),
        (UnsupportedAttachmentType, 415),
        (AttachmentProcessingError, 422),
        (StorageUnavailable, 503),
    ],
)
def test_domain_exception_maps_to_status(exc_type, status):
    @get("/boom")
    async def boom() -> None:
        raise exc_type("internal detail")

    app = Litestar([boom], exception_handlers=exception_handlers)
    with TestClient(app=app) as client:
        response = client.get("/boom")
    assert response.status_code == status
    assert "internal detail" not in response.text
