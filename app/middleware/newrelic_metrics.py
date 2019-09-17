from contextlib import ExitStack

from starlette.exceptions import ExceptionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.commons.instrumentation.newrelic import (
    web_transaction_from_request,
    set_transaction_name_from_request,
    set_request_id_from_request,
)


class NewRelicMetricsMiddleware(BaseHTTPMiddleware):
    enabled: bool

    def __init__(self, app: ExceptionMiddleware, *, enabled: bool = True):
        self.app = app
        self.enabled = enabled

    async def dispatch_func(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # early exit if newrelic is not enabled
        if not self.enabled:
            return await call_next(request)

        web_transaction = web_transaction_from_request(request)

        with ExitStack() as stack:
            # start the newrelic web transaction
            if web_transaction:
                stack.enter_context(web_transaction)

                # callback: set the request and correlation id
                stack.callback(set_request_id_from_request, request)
                # callback: set the transaction name from the resolved route
                stack.callback(set_transaction_name_from_request, request)

            # get response
            response = await call_next(request)
        return response
