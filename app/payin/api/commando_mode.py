from starlette.requests import Request
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.commons.api.models import PaymentException
from app.commons.context.req_context import is_req_commando_mode
from app.payin.core.exceptions import PayinErrorCode, CommandoModeShortCircuit


def commando_route_dependency(request: Request):
    commando_mode = is_req_commando_mode(request)
    if commando_mode and request.method in ("POST", "PATCH", "PUT"):
        http_status_code = HTTP_503_SERVICE_UNAVAILABLE

        internal_error = CommandoModeShortCircuit(
            error_code=PayinErrorCode.COMMANDO_DISABLED_ENDPOINT, retryable=False
        )

        raise PaymentException(
            http_status_code=http_status_code,
            error_code=internal_error.error_code,
            error_message=internal_error.error_message,
            retryable=internal_error.retryable,
        )
