from __future__ import annotations

from litestar.datastructures import State

from .data.db import JournalDb, UserDb
from .settings import settings


def create_users_db() -> UserDb:
    return UserDb(settings.db_path)


def create_journals_db() -> JournalDb:
    return JournalDb(settings.db_path)


def provide_users_db(state: State) -> UserDb:
    return state.users_db


def provide_journals_db(state: State) -> JournalDb:
    return state.journals_db
