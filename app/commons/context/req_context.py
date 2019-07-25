from typing import Any, cast
from dataclasses import dataclass

from starlette.requests import Request
from structlog import BoundLogger
from uuid import UUID, uuid4

from app.commons.context.app_context import AppContext


@dataclass
class ReqContext:
    req_id: UUID
    log: BoundLogger


def get_req_context(app_context: AppContext) -> ReqContext:
    req_id = uuid4()
    log = app_context.log.bind(req_id=req_id)
    return ReqContext(req_id=req_id, log=log)


def get_context_from_req(req: Request) -> ReqContext:
    state = cast(Any, req.state)
    req_context = cast(ReqContext, state.context)
    return req_context
