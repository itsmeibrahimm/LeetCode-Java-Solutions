from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request

from app.commons.applications import FastAPI
from app.commons.context.req_context import response_with_req_id, set_context_for_req


class ReqContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        context = set_context_for_req(request)
        context.log.debug("request context created")
        resp = await call_next(request)
        return response_with_req_id(request, resp)
