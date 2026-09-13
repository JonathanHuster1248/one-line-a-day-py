from pydantic_settings import BaseSettings
from enum import StrEnum
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class DbType(StrEnum):
    JSON = "json"
    SQL = "sql"


# DEFAULT_DB_PATH = str(Path(__file__).parent.resolve() / "data" / "test_db.json")
DEFAULT_DB_PATH = str(Path(__file__).parent.resolve() / "data" / "journal_entries.db")


class CoreSettings(BaseSettings):
    db_type: DbType = DbType.JSON
    db_path: str = DEFAULT_DB_PATH
    # TODO: Set db_path to be a Path type (unsure why I didn't have that already)
    session_cookie_secure: bool = False  # SESSION_COOKIE_SECURE=true in prod (HTTPS)
    cors_allowed_origins: list[str] = ["http://localhost:5173"]  # CORS_ALLOWED_ORIGINS
    # Matches any localhost/127.0.0.1 origin regardless of port, so local dev works
    # whether the frontend is reached via "localhost" or "127.0.0.1" or a different port.
    cors_allow_origin_regex: str = (
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"  # CORS_ALLOW_ORIGIN_REGEX
    )


settings = CoreSettings()
