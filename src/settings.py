from pydantic_settings import BaseSettings
from enum import StrEnum
from pathlib import Path

class DbType(StrEnum):
    JSON = "json"
    SQL = "sql"

DEFAULT_DB_PATH = Path(__file__).parent / "data" / "test_db.json"

class CoreSettings(BaseSettings):
    db_type: DbType = DbType.JSON
    db_path: str = DEFAULT_DB_PATH
    # TODO: Add user and password for auth

settings = CoreSettings()

