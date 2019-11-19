from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.types import CountryCode
from app.payin.api.payer.v0.request import UpdatePayerRequestV0
from app.payin.core.payer.model import Payer
from app.payin.core.payer.types import LegacyPayerInfo, PayerType
from app.payin.core.payer.v0.processor import PayerProcessorV0
from app.payin.core.types import PayerIdType

api_tags = ["PayerV0"]
router = APIRouter()


@router.get(
    "/payers/{payer_id_type}/{payer_id}",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="GetPayer",
    tags=api_tags,
)
async def get_payer(
    payer_id_type: PayerIdType,
    payer_id: str,
    payer_type: PayerType = None,
    country: CountryCode = CountryCode.US,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV0 = Depends(PayerProcessorV0),
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

    log.info("[get_payer] received request", payer_id=payer_id)
    payer = await payer_processor.get_payer(
        legacy_payer_info=LegacyPayerInfo(
            payer_id=payer_id,
            country=country,
            payer_id_type=payer_id_type,
            payer_type=payer_type,
        ),
        force_update=force_update,
    )
    log.info("[get_payer] retrieve_payer completed")
    return payer


@router.post(
    "/payers/{payer_id_type}/{payer_id}/default_payment_method",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="UpdatePayer",
    tags=api_tags,
)
async def update_default_payment_method(
    payer_id_type: PayerIdType,
    payer_id: str,
    req_body: UpdatePayerRequestV0,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV0 = Depends(PayerProcessorV0),
):
    """
    Update payer's default payment method

    - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_consumer_id",
      "stripe_customer_id", "dd_stripe_customer_id"
    - **payer_id**: DSJ legacy id
    - **country**: country of DoorDash payer (consumer)
    - **payer_type**: [string] identify the type of payer. Valid values include "marketplace",
                      "drive", "merchant", "store", "business" (default is "marketplace")
    - **default_payment_method**: [object] payer's payment method (source) on authorized Payment Provider
    - **default_payment_method.dd_stripe_card_id**: [string] primary key of MainDB.stripe_card table.

    """

    log.info("[update_payer] received request", payer_id=payer_id)
    return await payer_processor.update_default_payment_method(
        legacy_payer_info=LegacyPayerInfo(
            country=req_body.country,
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            payer_type=req_body.payer_type,
        ),
        dd_stripe_card_id=req_body.default_payment_method.dd_stripe_card_id,
    )
