from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str
    email: str = Field(unique=True, index=True)
    hashed_password: str


class UserPublic(SQLModel):
    id: UUID
    name: str
    email: str


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"
    __table_args__ = (UniqueConstraint("author_id", "date"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    author_id: UUID = Field(foreign_key="users.id")
    date: date
    message: str


class AttachmentKind(StrEnum):
    IMAGE = "image"
    PDF = "pdf"


class Attachment(SQLModel, table=True):
    __tablename__ = "attachments"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    entry_id: UUID = Field(
        foreign_key="journal_entries.id", ondelete="CASCADE", index=True
    )
    author_id: UUID = Field(foreign_key="users.id", index=True)  # denormalized owner
    filename: str  # original name, used only as display text
    kind: AttachmentKind
    content_type: str  # of the stored full-size content, e.g. image/webp
    size_bytes: int  # of the stored full-size content
    has_thumbnail: bool  # False for PDFs today
    width: int | None = None  # of the display copy; None for PDFs
    height: int | None = None
    original_content_type: str | None = None  # e.g. image/heic, before conversion
    content_hash: str | None = None  # sha256 of the uploaded bytes
    taken_at: datetime | None = None  # capture time from EXIF, if present
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AttachmentPublic(SQLModel):
    id: UUID
    entry_id: UUID
    filename: str
    kind: AttachmentKind
    content_type: str
    has_thumbnail: bool
    width: int | None = None
    height: int | None = None
