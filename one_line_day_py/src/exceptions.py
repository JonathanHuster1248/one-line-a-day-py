from litestar import Request, Response
from litestar.exceptions import NotFoundException
from litestar.exceptions.responses import create_exception_response
from litestar.types import ExceptionHandlersMap
from sqlalchemy.exc import NoResultFound


def handle_no_result_found(request: Request, exc: NoResultFound) -> Response:
    return create_exception_response(request, NotFoundException())


exception_handlers: ExceptionHandlersMap = {
    NoResultFound: handle_no_result_found,
}
