from __future__ import annotations

from datetime import date
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class JournalEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    date: date
    message: str
    photos: list[str] = Field(default_factory=list)


class JournalCreate(BaseModel):
    date: date
    message: str
    photos: list[str] = Field(default_factory=list)


class JournalUpdate(BaseModel):
    date: Optional[date] = None
    message: Optional[str] = None
    photos: list[str] = Field(default_factory=list)