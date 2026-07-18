from pydantic_settings import BaseSettings
from enum import StrEnum
from pathlib import Path

class DbType(StrEnum):
    JSON = "json"
    SQL = "sql"

DEFAULT_DB_PATH = str(Path(__file__).parent / "data" / "test_db.json")
# DEFAULT_DB_PATH = str(Path(__file__).parent / "data" / "journal_entries.db")

class CoreSettings(BaseSettings):
    db_type: DbType = DbType.JSON
    db_path: str = DEFAULT_DB_PATH
    # TODO: Set db_path to be a Path type (unsure why I didn't have that already)
    # TODO: Add user and password for auth

settings = CoreSettings()

