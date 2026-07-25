from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4
from pathlib import Path

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


class Photo(SQLModel, table=True):
    # TODO: Actually link this to a controller and make endpoints for it
    __tablename__ = "photos"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    entry_id: UUID = Field(foreign_key="journal_entries.id")
    file_path: Path
