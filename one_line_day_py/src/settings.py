from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


DEFAULT_DB_PATH = Path(__file__).parent.resolve() / "data" / "journal_entries.db"
DEFAULT_ATTACHMENTS_PATH = Path(__file__).parent.resolve() / "data" / "attachments"


class CoreSettings(BaseSettings):
    db_path: Path = DEFAULT_DB_PATH  # DB_PATH
    attachments_path: Path = DEFAULT_ATTACHMENTS_PATH  # ATTACHMENTS_PATH
    debug: bool = True  # DEBUG=false in prod (disables Litestar's debug tracebacks)
    session_cookie_secure: bool = False  # SESSION_COOKIE_SECURE=true in prod (HTTPS)
    cors_allowed_origins: list[str] = ["http://localhost:5173"]  # CORS_ALLOWED_ORIGINS
    # Matches any localhost/127.0.0.1 origin regardless of port, so local dev works
    # whether the frontend is reached via "localhost" or "127.0.0.1" or a different port.
    cors_allow_origin_regex: str = (
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"  # CORS_ALLOW_ORIGIN_REGEX
    )
    log_level: str = "INFO"  # LOG_LEVEL
    # Interface uvicorn binds to. Loopback by default so only this machine can reach
    # the API; the Docker image sets HOST=0.0.0.0 (compose limits exposure to loopback).
    host: str = "127.0.0.1"  # HOST
    # Serves Swagger UI and the OpenAPI schema at /schema. ENABLE_DOCS=false in prod.
    enable_docs: bool = True  # ENABLE_DOCS


settings = CoreSettings()
