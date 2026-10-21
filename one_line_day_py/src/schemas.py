from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel

from .model import AttachmentPublic, JournalEntry, User, UserPublic


class SignupPayload(BaseModel):
    name: str
    email: str
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str


class JournalEntryPublic(BaseModel):
    id: UUID
    author_id: UUID
    date: date
    message: str
    attachments: list[AttachmentPublic]
    # False only when the attachments lookup failed, so the UI can say so
    # instead of silently showing none.
    attachments_available: bool = True


def to_public_user(user: User) -> UserPublic:
    return UserPublic(id=user.id, name=user.name, email=user.email)


def to_public_entry(
    entry: JournalEntry, attachments: list[AttachmentPublic], available: bool = True
) -> JournalEntryPublic:
    return JournalEntryPublic(
        id=entry.id,
        author_id=entry.author_id,
        date=entry.date,
        message=entry.message,
        attachments=attachments,
        attachments_available=available,
    )
