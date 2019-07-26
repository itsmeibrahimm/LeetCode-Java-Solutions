from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from app.commons.context.req_context import set_context_for_req


class ReqContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        self.app = app

    async def dispatch_func(self, request: Request, call_next: RequestResponseEndpoint):
        context = set_context_for_req(request)
        context.log.debug("request context created")
        resp = await call_next(request)
        return resp
