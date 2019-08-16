from starlette.requests import Request
from fastapi import Header

from app.commons.context.app_context import AppContext, get_context_from_app
from app.commons.context.req_context import ReqContext, get_context_from_req


class RouteAuthorizer:
    def __init__(self, service_id):
        self.service_id = service_id

    async def __call__(self, request: Request, x_api_key: str = Header("")):
        app_context: AppContext = get_context_from_app(request.app)
        req_context: ReqContext = get_context_from_req(request)
        req_id = str(req_context.req_id)
        identity_client = app_context.identity_client
        temp = await identity_client.verify_api_key_with_http(
            service_id=self.service_id, api_key=x_api_key, correlation_id=req_id
        )

        req_context.log.info("Response: %s", temp)
