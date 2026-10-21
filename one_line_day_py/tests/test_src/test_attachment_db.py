import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest

from one_line_day_py.src.data.db import (
    MAX_ATTACHMENTS_PER_ENTRY,
    AttachmentDb,
    JournalDb,
    UserDb,
)
from one_line_day_py.src.exceptions import AttachmentLimitExceeded
from one_line_day_py.src.model import Attachment, AttachmentKind, JournalEntry, User


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test.db"


@pytest.fixture
def attachments_db(db_path: Path) -> AttachmentDb:
    return AttachmentDb(db_path)


def _make_user(db_path: Path, email: str) -> User:
    user = User(name=email, email=email, hashed_password="x")
    return run(UserDb(db_path).add_user(user))


def _make_entry(db_path: Path, user: User, day: int = 1) -> JournalEntry:
    from datetime import date

    entry = JournalEntry(author_id=user.id, date=date(2024, 1, day), message="m")
    return run(JournalDb(db_path).add_entry(entry))


def _attachment(
    entry: JournalEntry, user: User, created_at: datetime | None = None
) -> Attachment:
    att = Attachment(
        entry_id=entry.id,
        author_id=user.id,
        filename="a.png",
        kind=AttachmentKind.IMAGE,
        content_type="image/webp",
        size_bytes=1,
        has_thumbnail=True,
    )
    if created_at:
        att.created_at = created_at
    return att


def test_get_scoped_returns_match(db_path: Path, attachments_db: AttachmentDb) -> None:
    user = _make_user(db_path, "a@x.com")
    entry = _make_entry(db_path, user)
    att = run(attachments_db.add_attachment(_attachment(entry, user)))
    assert run(attachments_db.get_scoped(att.id, entry.id, user.id)).id == att.id


def test_get_scoped_rejects_wrong_entry_owner_and_missing(
    db_path: Path, attachments_db: AttachmentDb
) -> None:
    alice = _make_user(db_path, "a@x.com")
    bob = _make_user(db_path, "b@x.com")
    alice_entry = _make_entry(db_path, alice)
    bob_entry = _make_entry(db_path, bob)
    att = run(attachments_db.add_attachment(_attachment(alice_entry, alice)))

    assert run(attachments_db.get_scoped(att.id, bob_entry.id, alice.id)) is None
    assert run(attachments_db.get_scoped(att.id, alice_entry.id, bob.id)) is None
    assert run(attachments_db.get_scoped(att.id, bob_entry.id, bob.id)) is None
    assert run(attachments_db.get_scoped(uuid4(), alice_entry.id, alice.id)) is None


def test_list_is_ordered_by_created_at(
    db_path: Path, attachments_db: AttachmentDb
) -> None:
    user = _make_user(db_path, "a@x.com")
    entry = _make_entry(db_path, user)
    now = datetime.now(UTC)
    later = run(
        attachments_db.add_attachment(_attachment(entry, user, now + timedelta(1)))
    )
    earlier = run(attachments_db.add_attachment(_attachment(entry, user, now)))

    listed = run(attachments_db.list_for_entry(entry.id, user.id))
    assert [a.id for a in listed] == [earlier.id, later.id]


def test_list_for_entries_groups_and_scopes_by_author(
    db_path: Path, attachments_db: AttachmentDb
) -> None:
    alice = _make_user(db_path, "a@x.com")
    bob = _make_user(db_path, "b@x.com")
    e1 = _make_entry(db_path, alice, 1)
    e2 = _make_entry(db_path, alice, 2)
    e3 = _make_entry(db_path, bob, 3)
    a1 = run(attachments_db.add_attachment(_attachment(e1, alice)))
    run(attachments_db.add_attachment(_attachment(e3, bob)))

    result = run(attachments_db.list_for_entries([e1.id, e2.id, e3.id], alice.id))
    assert [a.id for a in result[e1.id]] == [a1.id]
    assert result[e2.id] == []
    assert result[e3.id] == []  # bob's attachment is invisible to alice


def test_list_for_entries_with_no_ids_is_empty(attachments_db: AttachmentDb) -> None:
    assert run(attachments_db.list_for_entries([], uuid4())) == {}


def test_sixth_attachment_is_rejected(
    db_path: Path, attachments_db: AttachmentDb
) -> None:
    user = _make_user(db_path, "a@x.com")
    entry = _make_entry(db_path, user)
    for _ in range(MAX_ATTACHMENTS_PER_ENTRY):
        run(attachments_db.add_attachment(_attachment(entry, user)))
    with pytest.raises(AttachmentLimitExceeded):
        run(attachments_db.add_attachment(_attachment(entry, user)))
    assert run(attachments_db.count_for_entry(entry.id)) == MAX_ATTACHMENTS_PER_ENTRY


def test_delete_and_count(db_path: Path, attachments_db: AttachmentDb) -> None:
    user = _make_user(db_path, "a@x.com")
    entry = _make_entry(db_path, user)
    att = run(attachments_db.add_attachment(_attachment(entry, user)))
    assert run(attachments_db.count_for_entry(entry.id)) == 1
    run(attachments_db.delete(att.id))
    assert run(attachments_db.count_for_entry(entry.id)) == 0


def test_existing_entry_ids(db_path: Path, attachments_db: AttachmentDb) -> None:
    user = _make_user(db_path, "a@x.com")
    entry = _make_entry(db_path, user)
    missing = uuid4()
    assert run(attachments_db.existing_entry_ids([entry.id, missing])) == {entry.id}
    assert run(attachments_db.existing_entry_ids([])) == set()
