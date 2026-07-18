from __future__ import annotations

from datetime import date
from typing import List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from sqlalchemy import Column
from sqlalchemy.types import JSON
from sqlmodel import SQLModel, Field


class JournalEntry(SQLModel, table=True):
    __tablename__ = "journal_entries"

    id: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    date: date
    message: str
    photos: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON)
    )


