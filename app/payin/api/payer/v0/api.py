from fastapi import APIRouter, Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.commons.types import CountryCode
from app.payin.api.payer.v0.request import UpdatePayerRequestV0
from app.payin.core.payer.model import Payer
from app.payin.core.payer.processor import PayerProcessor

from starlette.status import (
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
    HTTP_501_NOT_IMPLEMENTED,
    HTTP_400_BAD_REQUEST,
)

from app.payin.core.payer.types import PayerType
from app.payin.core.types import PayerIdType

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

    raise PaymentException(
        http_status_code=HTTP_501_NOT_IMPLEMENTED,
        error_code="not implemented",
        error_message="not implemented",
        retryable=False,
    )


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

    raise PaymentException(
        http_status_code=HTTP_501_NOT_IMPLEMENTED,
        error_code="not implemented",
        error_message="not implemented",
        retryable=False,
    )
