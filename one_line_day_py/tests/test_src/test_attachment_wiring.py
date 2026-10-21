import asyncio
import logging
from collections.abc import Coroutine
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from litestar import Litestar
from litestar.testing import TestClient

from one_line_day_py.main import make_app
from one_line_day_py.src.controllers.journal import AttachmentLookup
from one_line_day_py.src.dependencies import GuardedEntryAttachments
from one_line_day_py.src.model import AttachmentPublic
from one_line_day_py.src.services.attachments import AttachmentService
from one_line_day_py.src.settings import settings


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


class FakeService:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.removed: list[UUID] = []

    async def list_for_entries(
        self, user_id: UUID, entry_ids: list[UUID]
    ) -> dict[UUID, list[AttachmentPublic]]:
        if self.fail:
            raise RuntimeError("secret detail")
        return {entry_id: [] for entry_id in entry_ids}

    async def remove_entry_files(self, entry_id: UUID) -> None:
        if self.fail:
            raise OSError("secret detail")
        self.removed.append(entry_id)


def test_app_boots_with_attachment_state(app: Litestar, client: TestClient) -> None:
    assert isinstance(app.state.attachment_service, AttachmentService)
    assert isinstance(app.state.entry_attachments, GuardedEntryAttachments)
    assert app.state.attachment_service.journals_db is app.state.journals_db


def test_adapter_success() -> None:
    entry_id = uuid4()
    result = run(
        GuardedEntryAttachments(FakeService()).for_entries(uuid4(), [entry_id])
    )
    assert result == AttachmentLookup(by_entry={entry_id: []}, available=True)


def test_adapter_lookup_failure_is_swallowed(caplog: pytest.LogCaptureFixture) -> None:
    adapter = GuardedEntryAttachments(FakeService(fail=True))
    with caplog.at_level(logging.ERROR):
        result = run(adapter.for_entries(uuid4(), [uuid4()]))
    assert result == AttachmentLookup(by_entry={}, available=False)
    assert "RuntimeError" in caplog.text
    assert "secret detail" not in caplog.text


def test_adapter_remove_failure_is_swallowed(caplog: pytest.LogCaptureFixture) -> None:
    entry_id = uuid4()
    with caplog.at_level(logging.ERROR):
        run(
            GuardedEntryAttachments(FakeService(fail=True)).remove_entry_files(entry_id)
        )
    assert str(entry_id) in caplog.text
    assert "secret detail" not in caplog.text


def test_adapter_remove_delegates() -> None:
    service, entry_id = FakeService(), uuid4()
    run(GuardedEntryAttachments(service).remove_entry_files(entry_id))
    assert service.removed == [entry_id]


def test_startup_with_unwritable_attachments_dir_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setattr(settings, "db_path", tmp_path / "test.db")
    monkeypatch.setattr(settings, "attachments_path", blocker / "attachments")
    with TestClient(app=make_app()) as c:
        assert c.get("/ping").status_code == 200
