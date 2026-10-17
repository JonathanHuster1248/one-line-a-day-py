from __future__ import annotations

from pydantic import BaseModel

from .model import User, UserPublic


class SignupPayload(BaseModel):
    name: str
    email: str
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str


def to_public_user(user: User) -> UserPublic:
    return UserPublic(id=user.id, name=user.name, email=user.email)
