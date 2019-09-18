from fastapi import APIRouter, Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.commons.types import CountryCode

from starlette.requests import Request

from starlette.status import (
    HTTP_200_OK,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
    HTTP_501_NOT_IMPLEMENTED,
    HTTP_201_CREATED,
)

from app.commons.utils.types import PaymentProvider
from app.payin.api.payment_method.v0.request import CreatePaymentMethodRequestV0
from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.payment_method.model import PaymentMethod, PaymentMethodList
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import SortKey
from app.payin.core.types import PaymentMethodIdType

api_tags = ["PaymentMethodV0"]
router = APIRouter()


@router.post(
    "/payment_methods",
    response_model=PaymentMethod,
    status_code=HTTP_201_CREATED,
    operation_id="CreatePaymentMethod",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_payment_method(
    request: Request,
    req_body: CreatePaymentMethodRequestV0,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Create a payment method for payer on DoorDash payments platform

    - **token**: [string] Token from external PSP to collect sensitive card or bank account
                 details, or personally identifiable information (PII), directly from your customers.
    - **country**: [string] country code of DoorDash consumer
    - **dd_consumer_id**: [string][in legacy_payment_info] DoorDash consumer id.
    - **stripe_customer_id**: [string][in legacy_payment_info] Stripe customer id.
    """
    log.info(
        "[create_payment_method] receive request. ",
        dd_consumer_id=req_body.dd_consumer_id,
        stripe_customer_id=req_body.stripe_customer_id,
    )

    try:
        payment_method: PaymentMethod = await payment_method_processor.create_payment_method(
            pgp_code=PaymentProvider.STRIPE,
            token=req_body.token,
            dd_consumer_id=req_body.dd_consumer_id,
            stripe_customer_id=req_body.stripe_customer_id,
            country=req_body.country,
        )
        log.info(
            f"[create_payment_method] completed.",
            dd_consumer_id=req_body.dd_consumer_id,
            stripe_customer_id=req_body.stripe_customer_id,
        )
    except PaymentError as e:
        log.error(
            f"[create_payment_method] PaymentError.",
            dd_consumer_id=req_body.dd_consumer_id,
            stripe_customer_id=req_body.stripe_customer_id,
        )
        if e.error_code == PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT.value:
            http_status = HTTP_400_BAD_REQUEST
        elif e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND.value:
            http_status = HTTP_404_NOT_FOUND
        else:
            http_status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=http_status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return payment_method


@router.get(
    "/payment_methods/{payment_method_id_type}/{payment_method_id}",
    response_model=PaymentMethod,
    status_code=HTTP_200_OK,
    operation_id="GetPaymentMethod",
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_payment_method(
    request: Request,
    payment_method_id_type: PaymentMethodIdType,
    payment_method_id: str,
    country: CountryCode = CountryCode.US,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Get a payment method on DoorDash payments platform

    - **payment_method_id_type**: [string] identify the type of payment_method_id. Valid values include
      "stripe_payment_method_id", "dd_stripe_card_id"
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
      can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **country**: country of DoorDash payer (consumer)
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """

    log.info(
        f"[get_payment_method] receive request: payment_method_id={payment_method_id} payment_method_id_type={payment_method_id_type}"
    )

    try:
        payment_method: PaymentMethod = await payment_method_processor.get_payment_method(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
            country=country,
            force_update=force_update,
        )
    except PaymentError as e:
        log.warn(
            f"[get_payment_method][{payment_method_id}][{payment_method_id_type}] PaymentMethodReadError."
        )
        raise PaymentException(
            http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return payment_method


@router.get(
    "/payment_methods",
    response_model=PaymentMethodList,
    status_code=HTTP_200_OK,
    operation_id="ListPaymentMethods",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def list_payment_methods(
    request: Request,
    dd_consumer_id: str = None,
    stripe_cusotmer_id: str = None,
    country: CountryCode = CountryCode.US,
    active_only: bool = False,
    sort_by: SortKey = SortKey.CREATED_AT,
    force_update: bool = None,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    log.info(
        f"[list_payment_method] receive request dd_consumer_id:{dd_consumer_id} stripe_cusotmer_id:{stripe_cusotmer_id} country:{country} active_only:{active_only} force_update:{force_update}"
    )

    raise PaymentException(
        http_status_code=HTTP_501_NOT_IMPLEMENTED,
        error_code="not implemented",
        error_message="not implemented",
        retryable=False,
    )


@router.delete(
    "/payment_methods/{payment_method_id_type}/{payment_method_id}",
    response_model=PaymentMethod,
    status_code=HTTP_200_OK,
    operation_id="DeletePaymentMethod",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def delete_payment_method(
    request: Request,
    payment_method_id_type: PaymentMethodIdType,
    payment_method_id: str,
    country: CountryCode = CountryCode.US,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Detach a payment method for payer on DoorDash payments platform. If the detached payment method is the default
    one, DD payments platform will cleanup the Payer.default_payment_payment_method_id flag and it is client's
    responsibility to update the default payment method for invoice (Dashpass) use.

    - **payment_method_id_type**: [string] identify the type of payment_method_id. Valid values include
      "stripe_payment_method_id", "dd_stripe_card_id"
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
      can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **country**: country of DoorDash payer (consumer)
    """

    try:
        payment_method: PaymentMethod = await payment_method_processor.delete_payment_method(
            payment_method_id=payment_method_id,
            country=country,
            payment_method_id_type=payment_method_id_type,
        )
    except PaymentError as e:
        log.error(
            f"[delete_payment_method][{payment_method_id}][{payment_method_id_type}] PaymentMethodReadError."
        )
        if e.error_code == PayinErrorCode.PAYMENT_METHOD_GET_NOT_FOUND.value:
            http_status = HTTP_404_NOT_FOUND
        elif e.error_code in (
            PayinErrorCode.PAYMENT_METHOD_GET_PAYER_PAYMENT_METHOD_MISMATCH,
            PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
        ):
            http_status = HTTP_400_BAD_REQUEST
        else:
            http_status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=http_status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )

    return payment_method
