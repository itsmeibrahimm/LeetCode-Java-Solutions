from typing import Tuple

from fastapi import APIRouter, Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.commons.core.errors import PaymentError
from app.commons.types import CountryCode
from app.payin.api.payer.v0.request import UpdatePayerRequestV0
from app.payin.core.exceptions import PayinErrorCode, payin_error_message_maps
from app.payin.core.payer.model import Payer
from app.payin.core.payer.processor import PayerProcessor

from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
)

from app.payin.core.payer.types import PayerType
from app.payin.core.types import PayerIdType, PaymentMethodIdType

api_tags = ["PayerV0"]
router = APIRouter()


@router.get(
    "/payers/{payer_id_type}/{payer_id}",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="GetPayer",
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_payer(
    payer_id_type: PayerIdType,
    payer_id: str,
    country: CountryCode = CountryCode.US,
    payer_type: PayerType = None,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessor = Depends(PayerProcessor),
) -> Payer:
    """
    Get payer with DSJ legacy information.

    - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_consumer_id",
      "stripe_customer_id", "dd_stripe_customer_id"
    - **payer_id**: DSJ legacy id
    - **country**: country of DoorDash payer (consumer)
    - **payer_type**: [string] identify the type of payer. Valid values include "marketplace",
                      "drive", "merchant", "store", "business" (default is "marketplace")
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """

    log.info("[get_payer] payer_id=%s", payer_id)
    try:
        payer: Payer = await payer_processor.get_payer(
            payer_id=payer_id,
            country=country,
            payer_id_type=payer_id_type,
            payer_type=payer_type,
            force_update=force_update,
        )
        log.info("[get_payer] retrieve_payer completed")
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_404_NOT_FOUND
                if e.error_code
                in (
                    PayinErrorCode.PAYER_READ_NOT_FOUND,
                    PayinErrorCode.PAYER_READ_STRIPE_ERROR_NOT_FOUND,
                )
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return payer


@router.patch(
    "/payers/{payer_id_type}/{payer_id}",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="UpdatePayer",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def update_payer(
    payer_id_type: PayerIdType,
    payer_id: str,
    req_body: UpdatePayerRequestV0,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessor = Depends(PayerProcessor),
):
    """
    Update payer's default payment method

    - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_consumer_id",
      "stripe_customer_id", "dd_stripe_customer_id"
    - **payer_id**: DSJ legacy id
    - **country**: country of DoorDash payer (consumer)
    - **default_payment_method**: [object] payer's payment method (source) on authorized Payment Provider
    - **default_payment_method.dd_stripe_card_id**: [string] primary key of MainDB.stripe_card table.
    - **default_payment_method.stripe_payment_method_id**: [string] stripe's payment method id.
    """

    log.info("[update_payer] payer_id=%s", payer_id)
    try:

        # verify default_payment_method to ensure only one id is provided
        default_payment_method_id, payment_method_id_type = _verify_legacy_payment_method_id(
            req_body
        )

        payer: Payer = await payer_processor.update_payer(
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            default_payment_method_id=default_payment_method_id,
            country=req_body.country,
            payment_method_id_type=payment_method_id_type,
        )
    except PaymentError as e:
        if e.error_code == PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value:
            status = HTTP_400_BAD_REQUEST
        else:
            status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return payer


def _verify_legacy_payment_method_id(
    request: UpdatePayerRequestV0
) -> Tuple[str, PaymentMethodIdType]:
    payment_method_id: str
    payment_method_id_type: PaymentMethodIdType
    count: int = 0
    for key, value in request.default_payment_method:
        if value:
            payment_method_id = value
            payment_method_id_type = key
            count += 1

    if count != 1:
        raise PaymentException(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE,
            error_message=payin_error_message_maps[
                PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE
            ],
            retryable=False,
        )

    return payment_method_id, payment_method_id_type
