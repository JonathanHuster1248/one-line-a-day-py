from __future__ import annotations

from litestar import Controller, get
from litestar.response import File, Redirect


class RootController(Controller):
    path = "/"

    @get("/")
    async def entry(self) -> Redirect:
        return Redirect("/schema/swagger/")

    @get("/favicon.ico")
    async def get_favicon(self) -> File:
        return File(path="one_line_day_py/static/favicon.ico")

    @get("/ping")
    async def ping(self) -> dict[str, str]:
        return {"status": "ok"}
