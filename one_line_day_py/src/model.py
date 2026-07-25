from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlmodel import SQLModel, Field, UniqueConstraint


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"
    __table_args__ = (UniqueConstraint("author_id", "date"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    author_id: UUID = Field(foreign_key="users.id")
    date: date
    message: str
    # TODO: Turn the Photos into another table that has id, journal_id, and file_path
    photos: list[str] = Field(default_factory=list)
