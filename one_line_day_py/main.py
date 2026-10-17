from pathlib import Path

import uvicorn
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.datastructures import State
from litestar.di import Provide
from litestar.logging import LoggingConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.security.session_auth import SessionAuth
from litestar.stores.file import FileStore

from .src.controllers import (
    AuthController,
    JournalController,
    RootController,
    UserController,
    retrieve_user_handler,
)
from .src.dependencies import (
    create_journals_db,
    create_users_db,
    provide_journals_db,
    provide_users_db,
)
from .src.exceptions import exception_handlers
from .src.settings import settings

# Request/response bodies can contain passwords (auth) or private journal entries,
# so only path/method/status are logged, never headers/cookies/query/body.
logging_middleware_config = LoggingMiddlewareConfig(
    exclude=["^/schema", "^/favicon\\.ico$", "^/ping$"],
    request_log_fields=["path", "method"],
    response_log_fields=["status_code"],
)


def _make_logging_config() -> LoggingConfig:
    log_dir = Path(settings.db_path).parent / ".logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return LoggingConfig(
        formatters={
            "standard": {
                "format": "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
            }
        },
        handlers={
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "standard",
                "filename": str(log_dir / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
            },
            "queue_listener": {
                "class": "logging.handlers.QueueHandler",
                "queue": {"()": "queue.Queue", "maxsize": -1},
                "listener": "litestar.logging.standard.LoggingQueueListener",
                "handlers": ["console", "file"],
            },
        },
        loggers={
            "litestar": {
                "level": settings.log_level,
                "handlers": ["queue_listener"],
                "propagate": False,
            },
        },
        root={"level": settings.log_level, "handlers": ["queue_listener"]},
    )


def make_app():
    session_auth = SessionAuth(
        session_backend_config=ServerSideSessionConfig(
            secure=settings.session_cookie_secure
        ),
        retrieve_user_handler=retrieve_user_handler,
        exclude=[
            "^/schema",
            "^/favicon\\.ico$",
            "^/$",
            "^/ping$",
            "^/auth/(login|signup|logout)$",
        ],
    )

    return Litestar(
        route_handlers=[
            AuthController,
            RootController,
            JournalController,
            UserController,
        ],
        dependencies={
            "users_db": Provide(provide_users_db, sync_to_thread=False),
            "journals_db": Provide(provide_journals_db, sync_to_thread=False),
        },
        state=State(
            {"users_db": create_users_db(), "journals_db": create_journals_db()}
        ),
        exception_handlers=exception_handlers,
        cors_config=CORSConfig(
            allow_origins=settings.cors_allowed_origins,
            allow_origin_regex=settings.cors_allow_origin_regex,
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
        ),
        openapi_config=OpenAPIConfig(
            title="One Line a Day",
            description="Backend of one line a day application",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin()],
        ),
        on_app_init=[session_auth.on_app_init],
        stores={
            "sessions": FileStore(
                Path(settings.db_path).parent / ".sessions", create_directories=True
            )
        },
        logging_config=_make_logging_config(),
        middleware=[logging_middleware_config.middleware],
        debug=settings.debug,
    )


if __name__ == "__main__":
    uvicorn.run(
        "one_line_day_py.main:make_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
