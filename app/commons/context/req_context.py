from typing import Any, cast
from dataclasses import dataclass

from starlette.requests import Request
from structlog import BoundLogger
from uuid import UUID, uuid4

from app.commons.context.app_context import get_context_from_app, AppContext


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
