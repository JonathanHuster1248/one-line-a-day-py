from pathlib import Path

import uvicorn
from .src.app import (
    AuthController,
    JournalController,
    EntryController,
    UserController,
    retrieve_user_handler,
)
from litestar import Litestar
from litestar.config.cors import CORSConfig
from litestar.middleware.session.server_side import ServerSideSessionConfig
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.security.session_auth import SessionAuth
from litestar.stores.file import FileStore

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
            "^/hello_world$",
            "^/$",
            "^/auth/(login|signup|logout)$",
        ],
    )

    return Litestar(
        route_handlers=[
            AuthController,
            EntryController,
            JournalController,
            UserController,
        ],
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
        debug=True,
    )


if __name__ == "__main__":
    uvicorn.run(
        "one_line_day_py.main:make_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
