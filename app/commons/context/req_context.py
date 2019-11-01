from dataclasses import dataclass
from typing import Any, Optional, cast, List
from uuid import UUID, uuid4

from starlette.requests import Request
from starlette.responses import Response
from structlog.stdlib import BoundLogger

from app.commons.constants import (
    PAYMENT_REQUEST_ID_HEADER,
    EXTERNAL_CORRELATION_ID_HEADER,
)
from app.commons.context.app_context import AppContext, get_context_from_app
from app.commons.operational_flags import (
    STRIPE_COMMANDO_MODE_BOOLEAN,
    STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY,
    VERIFY_CARD_IN_COMMANDO_MODE,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.runtime import runtime
from app.commons.context.logger import set_request_id


@dataclass(frozen=True)
class ReqContext:
    req_id: UUID
    log: BoundLogger
    commando_mode: bool
    stripe_async_client: StripeAsyncClient
    commando_legacy_payment_white_list: List  # whitelist of consumer_ids
    verify_card_in_commando_mode: bool
    correlation_id: Optional[str] = None


def set_context_for_req(request: Request) -> ReqContext:
    assert not hasattr(request.state, "context"), "request context is already set"
    app_context = get_context_from_app(request.app)

    req_id = uuid4()
    set_request_id(req_id)
    correlation_id = request.headers.get(EXTERNAL_CORRELATION_ID_HEADER, None)
    log = app_context.log.bind(req_id=req_id, correlation_id=correlation_id)
    commando_mode = runtime.get_bool(STRIPE_COMMANDO_MODE_BOOLEAN, False)
    commando_legacy_payment_white_list = runtime.get_json(
        STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, []
    )
    verify_card_in_commando_mode = runtime.get_boolean(
        VERIFY_CARD_IN_COMMANDO_MODE, False
    )

    # Request specific Stripe Client, this allows us to inject request specific flags to control behavior on a
    # per request level
    stripe_async_client = StripeAsyncClient(
        executor_pool=app_context.stripe_thread_pool,
        stripe_client=app_context.stripe_client,
        commando=commando_mode,
    )
    req_context = ReqContext(
        req_id=req_id,
        log=log,
        commando_mode=commando_mode,
        correlation_id=correlation_id,
        stripe_async_client=stripe_async_client,
        commando_legacy_payment_white_list=commando_legacy_payment_white_list,
        verify_card_in_commando_mode=verify_card_in_commando_mode,
    )

    state = cast(Any, request.state)
    state.context = req_context

    return req_context


def get_context_from_req(request: Request) -> ReqContext:
    state = cast(Any, request.state)
    req_context = cast(ReqContext, state.context)
    return req_context


def build_req_context(app_context: AppContext, **additional_req_log_kwargs):
    req_id = uuid4()
    set_request_id(req_id)
    commando_mode = runtime.get_bool(STRIPE_COMMANDO_MODE_BOOLEAN, False)
    commando_legacy_payment_white_list = runtime.get_json(
        STRIPE_COMMANDO_LEGACY_CART_PAYMENT_WHITELIST_ARRAY, []
    )
    verify_card_in_commando_mode = runtime.get_boolean(
        VERIFY_CARD_IN_COMMANDO_MODE, False
    )

    # Request specific Stripe Client, this allows us to inject request specific flags to control behavior on a
    # per request level
    stripe_async_client = StripeAsyncClient(
        executor_pool=app_context.stripe_thread_pool,
        stripe_client=app_context.stripe_client,
        commando=commando_mode,
    )

    return ReqContext(
        req_id=req_id,
        log=app_context.log.bind(req_id=req_id, **additional_req_log_kwargs),
        commando_mode=commando_mode,
        stripe_async_client=stripe_async_client,
        commando_legacy_payment_white_list=commando_legacy_payment_white_list,
        verify_card_in_commando_mode=verify_card_in_commando_mode,
    )


def get_logger_from_req(request: Request) -> BoundLogger:
    return get_context_from_req(request).log


def is_req_commando_mode(request: Request) -> bool:
    return get_context_from_req(request).commando_mode


def get_legacy_payment_commando_whitelist(request: Request) -> List:
    return get_context_from_req(request).commando_legacy_payment_white_list


def response_with_req_id(request: Request, response: Response):
    req_id = str(get_context_from_req(request).req_id)
    response.headers[PAYMENT_REQUEST_ID_HEADER] = req_id
    return response


def override_commando_mode_context(request: Request, commando_mode: bool):
    old_ctxt = get_context_from_req(request)
    old_ctxt.stripe_async_client.commando = commando_mode
    req_context = ReqContext(
        req_id=old_ctxt.req_id,
        log=old_ctxt.log,
        commando_mode=commando_mode,
        correlation_id=old_ctxt.correlation_id,
        stripe_async_client=old_ctxt.stripe_async_client,
        commando_legacy_payment_white_list=old_ctxt.commando_legacy_payment_white_list,
        verify_card_in_commando_mode=old_ctxt.verify_card_in_commando_mode,
    )
    state = cast(Any, request.state)
    state.context = req_context

    return req_context


def get_stripe_async_client_from_req(request: Request) -> Optional[StripeAsyncClient]:
    """
    This should ALWAYS return a StripeAsyncClient when used in the context of a FastAPI request
    :param request:
    :return:
    """
    return get_context_from_req(request).stripe_async_client
