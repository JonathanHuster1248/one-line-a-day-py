from datetime import date
from uuid import uuid4

from one_line_day_py.src.model import AttachmentKind, AttachmentPublic, JournalEntry
from one_line_day_py.src.schemas import JournalEntryPublic, to_public_entry


def make_entry() -> JournalEntry:
    return JournalEntry(author_id=uuid4(), date=date(2024, 3, 1), message="hello")


def make_attachment(entry_id) -> AttachmentPublic:
    return AttachmentPublic(
        id=uuid4(),
        entry_id=entry_id,
        filename="a.png",
        kind=AttachmentKind.IMAGE,
        content_type="image/webp",
        has_thumbnail=True,
        width=10,
        height=10,
    )


def test_maps_entry_fields_and_attachments() -> None:
    entry = make_entry()
    attachment = make_attachment(entry.id)

    public = to_public_entry(entry, [attachment])

    assert public == JournalEntryPublic(
        id=entry.id,
        author_id=entry.author_id,
        date=entry.date,
        message=entry.message,
        attachments=[attachment],
        attachments_available=True,
    )


def test_unavailable_flag_passed_through() -> None:
    public = to_public_entry(make_entry(), [], available=False)

    assert public.attachments == []
    assert public.attachments_available is False


def test_serialized_shape() -> None:
    entry = make_entry()

    dumped = to_public_entry(entry, []).model_dump(mode="json")

    assert dumped == {
        "id": str(entry.id),
        "author_id": str(entry.author_id),
        "date": "2024-03-01",
        "message": "hello",
        "attachments": [],
        "attachments_available": True,
    }
