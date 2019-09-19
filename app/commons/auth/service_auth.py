from starlette.requests import Request
from fastapi import Header, HTTPException
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

from app.commons.context.app_context import AppContext, get_context_from_app
from app.commons.context.req_context import (
    ReqContext,
    get_context_from_req,
    get_logger_from_req,
)
from app.commons.providers.identity_client import (
    InternalIdentityBaseError,
    UnauthorizedError,
)


class ApiSecretRouteAuthorizer:
    def __init__(self, service_id):
        self.service_id = service_id

    async def __call__(
        self,
        request: Request,
        x_api_key: str = Header(""),
        dd_api_secret: str = Header(""),
    ):
        """
        https://doordash.atlassian.net/wiki/spaces/PE/pages/1017643094/Standard+headers
        IDS specifies non-standard header format, these need to be filtered in sentry/etc.

        :param request:
        :param x_api_key:
        :param dd_api_secret:
        :return:
        """
        app_context: AppContext = get_context_from_app(request.app)
        req_context: ReqContext = get_context_from_req(request)
        log = get_logger_from_req(request)
        req_id = str(req_context.req_id)
        identity_client = app_context.identity_client
        token = dd_api_secret or x_api_key
        try:
            await identity_client.verify_api_key_with_http(
                service_id=self.service_id, api_key=token, correlation_id=req_id
            )
        except UnauthorizedError as e:
            log.exception("Unauthorized Request")
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED, detail="Unauthorized API token"
            ) from e
        except InternalIdentityBaseError as e:
            log.exception("Auth Client Error")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Error occured while attempting to authorize with IDS",
            ) from e
        except Exception as e:
            log.exception("Auth Unknown Error")
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Error occured while attempting to authorize with IDS",
            ) from e
