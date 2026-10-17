from __future__ import annotations

from .data.db import JournalDb, UserDb
from .settings import settings

# TODO: Use Litestar's dependency injection for these instead of module-level
# singletons constructed at import time.
users_db = UserDb(settings.db_path)
journals_db = JournalDb(settings.db_path)
