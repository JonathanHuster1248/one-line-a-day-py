import asyncio
import io
import logging
from collections.abc import Coroutine
from datetime import date
from pathlib import Path
from typing import Any, NamedTuple, NoReturn
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy.exc import NoResultFound

from one_line_day_py.src.data.attachment_storage import AttachmentStorage, Variant
from one_line_day_py.src.data.db import AttachmentDb, JournalDb, UserDb
from one_line_day_py.src.exceptions import (
    AttachmentLimitExceeded,
    AttachmentProcessingError,
    AttachmentTooLarge,
    StorageUnavailable,
    UnsupportedAttachmentType,
)
from one_line_day_py.src.model import JournalEntry, User
from one_line_day_py.src.services.attachments import MAX_FILE_BYTES, AttachmentService


class Env(NamedTuple):
    service: AttachmentService
    storage: AttachmentStorage
    alice: User
    bob: User
    entry: JournalEntry
    journals_db: JournalDb


SECRET_NAME = "secret-holiday-name.png"
PDF = b"%PDF-1.4\n%fake\n"


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


def png(size: tuple[int, int] = (40, 20)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def env(tmp_path: Path) -> Env:
    db_path = tmp_path / "t.db"
    journals_db = JournalDb(db_path)
    storage = AttachmentStorage(tmp_path / "att")
    service = AttachmentService(AttachmentDb(db_path), storage, journals_db)
    users = UserDb(db_path)
    alice = run(users.add_user(User(name="a", email="a@x.com", hashed_password="x")))
    bob = run(users.add_user(User(name="b", email="b@x.com", hashed_password="x")))
    entry = run(
        journals_db.add_entry(
            JournalEntry(author_id=alice.id, date=date(2024, 1, 1), message="m")
        )
    )
    return Env(service, storage, alice, bob, entry, journals_db)


def test_add_image(env: Env) -> None:
    service, storage, alice, entry = env.service, env.storage, env.alice, env.entry
    result = run(service.add(alice.id, entry.id, SECRET_NAME, "image/png", png()))
    assert result.kind == "image"
    assert result.has_thumbnail
    assert result.content_type == "image/webp"
    assert (result.width, result.height) == (40, 20)
    assert storage.path_for(entry.id, result.id, Variant.THUMB)
    assert storage.path_for(entry.id, result.id, Variant.DISPLAY)


def test_add_pdf_stored_as_is(env: Env) -> None:
    service, storage, alice, entry = env.service, env.storage, env.alice, env.entry
    result = run(service.add(alice.id, entry.id, "a.pdf", "application/pdf", PDF))
    assert result.kind == "pdf"
    assert not result.has_thumbnail
    assert storage.path_for(entry.id, result.id, Variant.PDF).read_bytes() == PDF
    assert storage.path_for(entry.id, result.id, Variant.THUMB) is None


def test_domain_exceptions(env: Env) -> None:
    service, alice, entry = env.service, env.alice, env.entry
    with pytest.raises(AttachmentTooLarge):
        run(
            service.add(
                alice.id, entry.id, "a", "image/png", b"0" * (MAX_FILE_BYTES + 1)
            )
        )
    with pytest.raises(UnsupportedAttachmentType):
        run(service.add(alice.id, entry.id, "a.txt", "text/plain", b"hi"))
    with pytest.raises(UnsupportedAttachmentType):
        run(service.add(alice.id, entry.id, "a", None, b"hi"))
    with pytest.raises(AttachmentProcessingError):
        run(service.add(alice.id, entry.id, "a.png", "image/png", b"not an image"))
    with pytest.raises(AttachmentProcessingError):
        run(service.add(alice.id, entry.id, "a.pdf", "application/pdf", b"nope"))


def test_limit_exceeded_and_cleanup(env: Env) -> None:
    service, storage, alice, entry = env.service, env.storage, env.alice, env.entry
    for _ in range(5):
        run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    with pytest.raises(AttachmentLimitExceeded):
        run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    files = list((storage.root / str(entry.id)).iterdir())
    assert len(files) == 5 * 2  # the rejected upload left nothing behind


def test_other_users_entry_and_missing_entry_are_not_found(env: Env) -> None:
    service, bob, entry = env.service, env.bob, env.entry
    with pytest.raises(NoResultFound):
        run(service.add(bob.id, entry.id, "a.png", "image/png", png()))
    with pytest.raises(NoResultFound):
        run(service.add(bob.id, uuid4(), "a.png", "image/png", png()))


def test_failed_insert_removes_files(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    service, storage, alice, entry = env.service, env.storage, env.alice, env.entry

    async def boom(_):
        raise RuntimeError("db down")

    monkeypatch.setattr(service.attachments_db, "add_attachment", boom)
    with pytest.raises(RuntimeError):
        run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    assert not (storage.root / str(entry.id)).exists()


def test_unwritable_storage_raises_and_leaves_no_row(env: Env, tmp_path: Path) -> None:
    service, alice, entry = env.service, env.alice, env.entry
    blocker = tmp_path / "file"
    blocker.write_text("x")
    service.storage = AttachmentStorage(blocker / "att")
    with pytest.raises(StorageUnavailable):
        run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    assert run(service.list_for_entry(alice.id, entry.id)) == []


def test_list_for_entry_and_entries(env: Env) -> None:
    service, alice, bob, entry = env.service, env.alice, env.bob, env.entry
    added = run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    assert [a.id for a in run(service.list_for_entry(alice.id, entry.id))] == [added.id]
    with pytest.raises(NoResultFound):
        run(service.list_for_entry(bob.id, entry.id))
    assert run(service.list_for_entries(bob.id, [entry.id])) == {entry.id: []}
    assert run(service.list_for_entries(alice.id, [])) == {}


def test_open_variants(env: Env) -> None:
    service, storage, alice, entry = env.service, env.storage, env.alice, env.entry
    img = run(service.add(alice.id, entry.id, "photo.png", "image/png", png()))
    pdf = run(service.add(alice.id, entry.id, "doc.pdf", "application/pdf", PDF))

    thumb = run(service.open(alice.id, entry.id, img.id, thumbnail=True))
    assert thumb.path == storage.path_for(entry.id, img.id, Variant.THUMB)
    assert thumb.content_type == "image/webp"

    full = run(service.open(alice.id, entry.id, img.id))
    assert full.path == storage.path_for(entry.id, img.id, Variant.DISPLAY)
    assert full.filename == "photo.png"

    doc = run(service.open(alice.id, entry.id, pdf.id))
    assert doc.content_type == "application/pdf"
    assert doc.path == storage.path_for(entry.id, pdf.id, Variant.PDF)

    with pytest.raises(NoResultFound):
        run(service.open(alice.id, entry.id, pdf.id, thumbnail=True))


def test_open_denies_wrong_owner_wrong_entry_and_missing_file(env: Env) -> None:
    service, storage, alice, bob, entry, journals_db = (
        env.service,
        env.storage,
        env.alice,
        env.bob,
        env.entry,
        env.journals_db,
    )
    img = run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    other = run(
        journals_db.add_entry(
            JournalEntry(author_id=bob.id, date=date(2024, 1, 2), message="m")
        )
    )
    with pytest.raises(NoResultFound):
        run(service.open(bob.id, entry.id, img.id))
    with pytest.raises(NoResultFound):
        run(service.open(bob.id, other.id, img.id))
    storage.path_for(entry.id, img.id, Variant.DISPLAY).unlink()
    with pytest.raises(NoResultFound):
        run(service.open(alice.id, entry.id, img.id))


def test_delete_removes_row_then_files(env: Env) -> None:
    service, storage, alice, bob, entry = (
        env.service,
        env.storage,
        env.alice,
        env.bob,
        env.entry,
    )
    img = run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    with pytest.raises(NoResultFound):
        run(service.delete(bob.id, entry.id, img.id))
    run(service.delete(alice.id, entry.id, img.id))
    assert run(service.list_for_entry(alice.id, entry.id)) == []
    assert not (storage.root / str(entry.id)).exists()


def test_sweep_removes_only_orphan_directories(env: Env) -> None:
    service, storage, alice, entry = env.service, env.storage, env.alice, env.entry
    run(service.add(alice.id, entry.id, "a.png", "image/png", png()))
    orphan = uuid4()
    storage.save(orphan, uuid4(), Variant.PDF, b"x")
    (storage.root / "not-a-uuid").mkdir()

    run(service.sweep_orphans())

    assert (storage.root / str(entry.id)).is_dir()
    assert not (storage.root / str(orphan)).exists()
    assert (storage.root / "not-a-uuid").is_dir()


def test_sweep_never_raises(
    env: Env, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    service = env.service

    def boom() -> NoReturn:
        raise OSError("disk")

    monkeypatch.setattr(service.storage, "entry_dirs", boom)
    with caplog.at_level(logging.ERROR):
        run(service.sweep_orphans())
    assert "OSError" in caplog.text


def test_logs_contain_nothing_sensitive(
    env: Env, caplog: pytest.LogCaptureFixture
) -> None:
    service, alice, entry = env.service, env.alice, env.entry
    with caplog.at_level(logging.DEBUG):
        run(service.add(alice.id, entry.id, SECRET_NAME, "image/png", png()))
        with pytest.raises(AttachmentProcessingError):
            run(service.add(alice.id, entry.id, SECRET_NAME, "image/png", b"garbage!"))
    assert SECRET_NAME not in caplog.text
    assert "garbage" not in caplog.text
    assert "secret-holiday" not in caplog.text
