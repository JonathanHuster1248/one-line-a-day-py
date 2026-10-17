from __future__ import annotations

from .data.sql_back import JournalSqlDb, UserSqlDb
from .settings import settings

# TODO: Use Litestar's dependency injection for these instead of module-level
# singletons constructed at import time.
users_db = UserSqlDb(settings.db_path)
journals_db = JournalSqlDb(settings.db_path)
