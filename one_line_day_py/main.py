from importlib.metadata import version

import uvicorn
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.datastructures import State
from litestar.di import Provide
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
from .src.logging_config import create_logging_config, logging_middleware_config
from .src.settings import settings


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
        openapi_config=(
            OpenAPIConfig(
                title="One Line a Day",
                description="Backend of one line a day application",
                version=version("one-line-day-py"),
                render_plugins=[SwaggerRenderPlugin()],
            )
            if settings.enable_docs
            else None
        ),
        on_app_init=[session_auth.on_app_init],
        stores={
            "sessions": FileStore(
                settings.db_path.parent / ".sessions", create_directories=True
            )
        },
        logging_config=create_logging_config(),
        middleware=[logging_middleware_config.middleware],
        debug=settings.debug,
    )


if __name__ == "__main__":
    uvicorn.run(
        "one_line_day_py.main:make_app",
        factory=True,
        host=settings.host,
        port=8000,
        reload=True,
    )
