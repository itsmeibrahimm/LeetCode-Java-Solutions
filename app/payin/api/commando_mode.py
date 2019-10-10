from starlette.requests import Request
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE

from app.commons.api.models import PaymentException
from app.commons.context.req_context import (
    is_req_commando_mode,
    get_legacy_payment_commando_whitelist,
    override_commando_mode_context,
)
from app.payin.api.cart_payment.v0.request import CreateCartPaymentLegacyRequest
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


def override_commando_mode_legacy_cart_payment(
    request: Request, cart_payment_request: CreateCartPaymentLegacyRequest
) -> CreateCartPaymentLegacyRequest:
    dd_consumer_id = cart_payment_request.legacy_payment.dd_consumer_id

    if dd_consumer_id in get_legacy_payment_commando_whitelist(request):
        override_commando_mode_context(request, True)

    return cart_payment_request
