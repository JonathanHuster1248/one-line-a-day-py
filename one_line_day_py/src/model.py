from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4
from pydantic import Field

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import SQLModel, Field, UniqueConstraint


class User(SQLModel):
    name: str


class UserTable(User, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True, index=True)



class JournalEntry(SQLModel):
    date: date
    message: str
    photos: list[str] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )


class JournalTable(JournalEntry, table=True):
    __tablename__ = "journal_entries"
    __table_args__ = (
        UniqueConstraint("author_id", "date"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    author_id:int = Field(foreign_key="user.id")


