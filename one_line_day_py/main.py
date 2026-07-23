from .src.app import JournalController, EntryController, UserController
from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig
from litestar.openapi.plugins import SwaggerRenderPlugin


def make_app():
    return Litestar(
        route_handlers=[EntryController, JournalController, UserController],
        openapi_config=OpenAPIConfig(
            title="One Line a Day",
            description="Backend of one line a day application",
            version="0.0.1",
            render_plugins=[SwaggerRenderPlugin()],
        ),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "one_line_day_py.main:make_app",
        factory=True,
        port=8000,
        reload=True,
    )
