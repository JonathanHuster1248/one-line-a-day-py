from __future__ import annotations

from uuid import UUID

from litestar import Controller, Request, get, post, put, delete
from litestar.exceptions import HTTPException, NotAuthorizedException, NotFoundException
from litestar.params import FromQuery
from litestar.response import File, Redirect
from litestar.status_codes import HTTP_409_CONFLICT
from pydantic import BaseModel
from sqlalchemy.exc import NoResultFound

from datetime import date
from typing import Optional

from .model import JournalEntry, User, UserPublic
from .security import hash_password, verify_password
from .settings import settings
from .data.sql_back import UserSqlDb, JournalSqlDb

users_db = UserSqlDb(settings.db_path)
journals_db = JournalSqlDb(settings.db_path)


async def retrieve_user_handler(session: dict, connection) -> User | None:
    user_id = session.get("user_id")
    if user_id is None:
        return None
    try:
        return await users_db.get_user_by_id(UUID(user_id))
    except NoResultFound:
        return None


def _to_public(user: User) -> UserPublic:
    return UserPublic(id=user.id, name=user.name, email=user.email)


class SignupPayload(BaseModel):
    name: str
    email: str
    password: str


class LoginPayload(BaseModel):
    email: str
    password: str


class EntryController(Controller):
    path = "/"

    @get("/")
    async def entry(self) -> Redirect:
        return Redirect("/schema/swagger/")

    @get("/hello_world")
    async def hello_world(self) -> str:
        return "Hello World!"

    @get("/favicon.ico")
    async def get_favicon(self) -> File:
        return File(path="one_line_day_py/static/favicon.ico")


class AuthController(Controller):
    path = "/auth"

    @post("/signup", exclude_from_auth=True)
    async def signup(self, request: Request, data: SignupPayload) -> UserPublic:
        if await users_db.get_user_by_email(data.email) is not None:
            raise HTTPException(
                status_code=HTTP_409_CONFLICT, detail="Email already registered"
            )

        user = User(
            name=data.name,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        await users_db.add_user(user)
        request.set_session({"user_id": str(user.id)})
        return _to_public(user)

    @post("/login", exclude_from_auth=True)
    async def login(self, request: Request, data: LoginPayload) -> UserPublic:
        user = await users_db.get_user_by_email(data.email)
        if user is None or not verify_password(data.password, user.hashed_password):
            raise NotAuthorizedException(detail="Invalid email or password")

        request.set_session({"user_id": str(user.id)})
        return _to_public(user)

    @post("/logout", exclude_from_auth=True)
    async def logout(self, request: Request) -> None:
        request.clear_session()

    @get("/me")
    async def me(self, request: Request) -> UserPublic:
        return _to_public(request.user)


class UserController(Controller):
    path = "/users"

    @get("/")
    async def list_users(self) -> list[UserPublic]:
        users = await users_db.list_users()
        return [_to_public(user) for user in users]

    @get("/{user_id:uuid}")
    async def get_user_by_id(self, user_id: UUID) -> UserPublic:
        user = await users_db.get_user_by_id(user_id)
        return _to_public(user)

    @get("/name/{user_name:str}")
    async def get_user_by_name(self, user_name: str) -> UserPublic:
        user = await users_db.get_user_id_by_name(user_name)
        return _to_public(user)

    @put("/{user_id:uuid}")
    async def update_user(
        self, user_id: UUID, name: Optional[str] = None
    ) -> UserPublic:
        existing_user = await users_db.get_user_by_id(user_id)

        name = name or existing_user.name

        updated_user = User(
            id=user_id,
            name=name,
            email=existing_user.email,
            hashed_password=existing_user.hashed_password,
        )
        user = await users_db.update_user(updated_user)
        return _to_public(user)

    @delete("/{user_id:uuid}")
    async def delete_user(self, user_id: UUID) -> None:
        await users_db.delete_user(user_id)


# TODO: Use Litestar's dependency injection for this instead of just relying on db being made at the top of the file
class JournalController(Controller):
    path = "/journals"

    @post("/")
    async def create_entry(
        self, request: Request, date: date, message: str
    ) -> JournalEntry:
        entry = JournalEntry(author_id=request.user.id, date=date, message=message)
        uploaded_entry = await journals_db.add_entry(entry)
        return uploaded_entry

    @get("/")
    async def list_entries(
        self,
        request: Request,
        month: FromQuery[int | None] = None,
        day: FromQuery[int | None] = None,
        year: FromQuery[int | None] = None,
    ) -> list[JournalEntry]:
        entries = await journals_db.list_entries(request.user.id, month, day, year)
        return entries

    @get("/{entry_id:uuid}")
    async def get_entry(self, request: Request, entry_id: UUID) -> JournalEntry:
        entry = await journals_db.get_entry(entry_id)
        if entry.author_id != request.user.id:
            raise NotFoundException()
        return entry

    @get("/{entry_id:uuid}/author")
    async def get_entry_author(self, request: Request, entry_id: UUID) -> UUID:
        author_id = await journals_db.get_entry_author(entry_id)
        if author_id != request.user.id:
            raise NotFoundException()
        return author_id

    @put("/{entry_id:uuid}")
    async def update_entry(
        self,
        request: Request,
        entry_id: UUID,
        input_date: Optional[date] = None,
        message: Optional[str] = None,
    ) -> JournalEntry:
        existing_entry = await journals_db.get_entry(entry_id)
        if existing_entry.author_id != request.user.id:
            raise NotFoundException()

        input_date = input_date or existing_entry.date
        message = message or existing_entry.message

        updated_entry = JournalEntry(
            id=entry_id,
            author_id=existing_entry.author_id,
            date=input_date,
            message=message,
        )
        await journals_db.update_entry(updated_entry)

        return updated_entry

    @delete("/{entry_id:uuid}")
    async def delete_entry(self, request: Request, entry_id: UUID) -> None:
        existing_entry = await journals_db.get_entry(entry_id)
        if existing_entry.author_id != request.user.id:
            raise NotFoundException()
        await journals_db.delete_entry(entry_id)
