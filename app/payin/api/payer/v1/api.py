from typing import Union, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.payin.api.payer.v1.request import CreatePayerRequest, UpdatePayerRequestV1
from app.payin.core.exceptions import PayinError, PayinErrorCode
from app.payin.core.payer.model import Payer
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.types import PayerReferenceIdType

api_tags = ["PayerV1"]
router = APIRouter()


@router.post(
    "/payers",
    response_model=Payer,
    status_code=HTTP_201_CREATED,
    responses={HTTP_200_OK: {"model": Payer}},
    operation_id="CreatePayer",
    tags=api_tags,
)
async def create_payer(
    req_body: CreatePayerRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
) -> Union[JSONResponse, Payer]:
    """
    Create a payer on DoorDash payments platform

    - **payer_correlation_ids**: DoorDash external correlation id for Payer.
    - **payer_correlation_ids.payer_reference_id**: DoorDash external reference id for Payer.
    - **payer_correlation_ids.payer_reference_id_type**: type that specifies the role of payer.
    - **email**: payer email.
    - **country**: payer country. It will be used by payment gateway provider.
    - **description**: a description of payer.
    """
    log.info(
        "[create_payer] receive request.",
        payer_reference_id=req_body.payer_correlation_ids.payer_reference_id,
        payer_reference_id_type=req_body.payer_correlation_ids.payer_reference_id_type,
    )

    # Currently all payer_reference_id are all numeric.
    try:
        int(req_body.payer_correlation_ids.payer_reference_id)
    except ValueError:
        log.exception(
            "[create_payer] Value error for non-numeric value.",
            payer_reference_id=req_body.payer_correlation_ids.payer_reference_id,
            payer_reference_id_type=req_body.payer_correlation_ids.payer_reference_id_type,
        )
        raise PayinError(error_code=PayinErrorCode.PAYER_CREATE_INVALID_DATA)

    create_payer_result: Tuple[Payer, bool] = await payer_processor.create_payer(
        payer_reference_id=req_body.payer_correlation_ids.payer_reference_id,
        payer_reference_id_type=req_body.payer_correlation_ids.payer_reference_id_type,
        email=req_body.email,
        country=req_body.country,
        description=req_body.description,
    )
    payer, already_exists = create_payer_result
    if already_exists:
        return JSONResponse(status_code=HTTP_200_OK, content=jsonable_encoder(payer))
    log.info("[create_payer] completed.")
    return payer


@router.get(
    "/payers/{payer_id}",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="GetPayer",
    tags=api_tags,
)
async def get_payer(
    payer_id: UUID,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
) -> Payer:
    """
    Get payer.

    - **payer_id**: DoorDash payer_id
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """
    log.info("[get_payer] received request.", payer_id=payer_id)
    return await payer_processor.get_payer(
        payer_lookup_id=payer_id,
        payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
        force_update=force_update,
    )


@router.get(
    "/payers/{payer_reference_id_type}/{payer_reference_id}",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="GetPayerByReferenceId",
    tags=api_tags,
)
async def get_payer_by_reference_id(
    payer_reference_id_type: PayerReferenceIdType,
    payer_reference_id: str,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
) -> Payer:
    """
    Get payer by payer reference id and type.

    - **payer_reference_id_type**: DoorDash payer_reference_id_type
    - **payer_reference_id**: DoorDash payer_reference_id
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """
    log.info(
        "[get_payer_by_reference_id] received request.",
        payer_reference_id_type=payer_reference_id_type,
        payer_reference_id=payer_reference_id,
    )
    return await payer_processor.get_payer(
        payer_lookup_id=payer_reference_id,
        payer_reference_id_type=payer_reference_id_type,
        force_update=force_update,
    )


@router.post(
    "/payers/{payer_id}/default_payment_method",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="UpdatePayerDefaultPaymentMethodById",
    tags=api_tags,
)
async def update_default_payment_method(
    payer_id: UUID,
    req_body: UpdatePayerRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
):
    """
    Update payer's default payment method

    - **payer_id**: DoorDash payer_id
    - **default_payment_method**: payer's payment method (source) on authorized Payment Provider
    - **default_payment_method.payment_method_id**: [UUID] identity of the payment method.
    - **default_payment_method.dd_stripe_card_id**: [string] legacy primary id of StripeCard object
    """

    log.info("[update_payer] received request", payer_id=payer_id)
    # verify default_payment_method to ensure only one id is provided
    _verify_payment_method_id(req_body)

    return await payer_processor.update_default_payment_method(
        payer_lookup_id=payer_id,
        payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
        payment_method_id=req_body.default_payment_method.payment_method_id,
        dd_stripe_card_id=req_body.default_payment_method.dd_stripe_card_id,
    )


@router.post(
    "/payers/{payer_reference_id_type}/{payer_reference_id}/default_payment_method",
    response_model=Payer,
    status_code=HTTP_200_OK,
    operation_id="UpdatePayerDefaultPaymentMethodByReference",
    tags=api_tags,
)
async def update_default_payment_method_by_reference_id(
    payer_reference_id_type: PayerReferenceIdType,
    payer_reference_id: str,
    req_body: UpdatePayerRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    payer_processor: PayerProcessorV1 = Depends(PayerProcessorV1),
):
    """
    Update payer's default payment method by payer reference id and type.

    - **payer_reference_id_type**: DoorDash payer_reference_id_type
    - **payer_reference_id**: DoorDash payer_reference_id
    - **default_payment_method**: payer's payment method (source) on authorized Payment Provider
    - **default_payment_method.payment_method_id**: [UUID] identity of the payment method.
    - **default_payment_method.dd_stripe_card_id**: [string] legacy primary id of StripeCard object
    """

    log.info(
        "[update_default_payment_method_by_reference_id] received request",
        payer_reference_id_type=payer_reference_id_type,
        payer_reference_id=payer_reference_id,
    )
    # verify default_payment_method to ensure only one id is provided
    _verify_payment_method_id(req_body)

    return await payer_processor.update_default_payment_method(
        payer_lookup_id=payer_reference_id,
        payer_reference_id_type=payer_reference_id_type,
        payment_method_id=req_body.default_payment_method.payment_method_id,
        dd_stripe_card_id=req_body.default_payment_method.dd_stripe_card_id,
    )


def _verify_payment_method_id(request: UpdatePayerRequestV1):
    count: int = 0
    for key, value in request.default_payment_method:
        if value:
            count += 1

    if count != 1:
        raise PayinError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYMENT_METHOD_TYPE
        )
