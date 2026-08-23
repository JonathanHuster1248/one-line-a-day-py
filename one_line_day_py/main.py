import uvicorn
from .src.app import JournalController, EntryController, UserController
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin
from litestar.config.cors import CORSConfig


def make_app():
    return Litestar(
        route_handlers=[EntryController, JournalController, UserController],
        cors_config=CORSConfig(
            allow_origins=[
                "*",
            ],
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        openapi_config=OpenAPIConfig(
            title="One Line a Day",
            description="Backend of one line a day application",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin()],
        ),
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
