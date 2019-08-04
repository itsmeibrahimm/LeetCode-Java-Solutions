import logging
from pydantic import BaseModel

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from app.commons.error.errors import PaymentErrorResponseBody
from app.payin.api.payer.v1.request import CreatePayerRequest, UpdatePayerRequest
from app.payin.core.exceptions import (
    PayerCreationError,
    PayinErrorCode,
    PayerUpdateError,
)
from app.payin.core.payer.model import Payer
from app.payin.core.payer.processor import (
    onboard_payer,
    retrieve_payer,
    update_payer_default_payment_method,
)

from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_200_OK,
)

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/api/v1/payers", status_code=HTTP_201_CREATED)
async def create_payer(req_body: CreatePayerRequest):
    """
    Create a payer on DoorDash payments platform

    - **dd_payer_id**: DoorDash consumer_id, store_id, or business_id
    - **payer_type**: type that specifies the role of payer
    - **email**: payer email
    - **country**: payer country. It will be used by payment gateway provider.
    - **description**: a description of payer
    """
    logger.info("create_payer()")

    try:
        payer: Payer = await onboard_payer(
            req_body.dd_payer_id,
            req_body.payer_type,
            req_body.email,
            req_body.country,
            req_body.description,
        )
        logger.info("[create_payer] onboard_payer() completed.")
    except PayerCreationError as e:
        # raise PaymentException(http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        #                        error_code=e.error_code,
        #                        error_message=e.error_message,
        #                        retryable=e.retryable)
        return create_response_blob(
            HTTP_500_INTERNAL_SERVER_ERROR,
            PaymentErrorResponseBody(
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            ),
        )

    return payer


@router.get("/api/v1/payers/{payer_id}", status_code=HTTP_200_OK)
async def get_payer(payer_id: str, payer_type: str = None):
    """
    Get payer.

    - **payer_id**: DoorDash payer_id or stripe_customer_id
    """
    logger.info("[get_payer] payer_id=%s", payer_id)
    try:
        payer: Payer = await retrieve_payer(payer_id=payer_id, payer_type=payer_type)
        logger.info("[get_payer] retrieve_payer completed")
    except PayerCreationError as e:
        return create_response_blob(
            (
                HTTP_404_NOT_FOUND
                if e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND.value
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            PaymentErrorResponseBody(
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            ),
        )

    return payer


@router.patch("/api/v1/payers/{payer_id}", status_code=HTTP_200_OK)
async def update_payer(payer_id: str, req_body: UpdatePayerRequest):
    """
    Update payer's default payment method

    - **default_payment_method_id**: payer's payment method (source) on authorized Payment Provider
    """
    logger.info("[update_payer] payer_id=%s", payer_id)

    try:
        payer: Payer = await update_payer_default_payment_method(
            payer_id=payer_id,
            default_payment_method_id=req_body.default_payment_method_id,
            default_source_id=req_body.default_source_id,
            default_card_id=req_body.default_card_id,
            payer_id_type=req_body.payer_id_type,
            payer_type=req_body.payer_type,
        )
    except PayerUpdateError as e:
        status = (
            HTTP_400_BAD_REQUEST
            if e.error_code == PayinErrorCode.PAYER_UPDATE_DB_ERROR_INVALID_DATA.value
            else HTTP_500_INTERNAL_SERVER_ERROR
        )
        return create_response_blob(
            status,
            PaymentErrorResponseBody(
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            ),
        )

    return payer


def create_response_blob(status_code: int, resp_blob: BaseModel):
    # FIXME: will be replaced by PaymentException
    return JSONResponse(status_code=status_code, content=jsonable_encoder(resp_blob))
