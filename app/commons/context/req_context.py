from dataclasses import dataclass
from typing import Any, cast
from uuid import UUID, uuid4

from starlette.requests import Request
from starlette.responses import Response
from structlog import BoundLogger

from app.commons.constants import PAYMENT_REQUEST_ID_HEADER
from app.commons.context.app_context import AppContext, get_context_from_app


@dataclass(frozen=True)
class ReqContext:
    req_id: UUID
    log: BoundLogger


def set_context_for_req(request: Request) -> ReqContext:
    assert not hasattr(request.state, "context"), "request context is already set"
    app_context = get_context_from_app(request.app)

    req_id = uuid4()
    log = app_context.log.bind(req_id=req_id)
    req_context = ReqContext(req_id=req_id, log=log)

    state = cast(Any, request.state)
    state.context = req_context

    return req_context


def get_context_from_req(request: Request) -> ReqContext:
    state = cast(Any, request.state)
    req_context = cast(ReqContext, state.context)
    return req_context


def build_req_context(app_context: AppContext):
    req_id = uuid4()
    return ReqContext(req_id=req_id, log=app_context.log.bind(req_id=req_id))


def get_logger_from_req(request: Request):
    return get_context_from_req(request).log


def response_with_req_id(request: Request, response: Response):
    req_id = str(get_context_from_req(request).req_id)
    response.headers[PAYMENT_REQUEST_ID_HEADER] = req_id
    return response
