import logging
from pydantic import BaseModel

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder

from app.payin.api.payer.v1.request import CreatePayerRequest
from app.payin.core.payer.model import Payer
from app.payin.core.payer.processor import onboard_payer

from starlette.responses import JSONResponse
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_501_NOT_IMPLEMENTED,
)

from app.payin.api.payer.v1.response import HttpResponseBlob

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/api/v1/payers", status_code=HTTP_201_CREATED)
async def create_payer(reqBody: CreatePayerRequest):
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
            reqBody.dd_payer_id,
            reqBody.payer_type,
            reqBody.email,
            reqBody.country,
            reqBody.description,
        )
        logger.info("onboard_payer() completed. ")
    except Exception as e:
        logger.error("onboard_payer() exception", e)
        return create_response_blob(
            HTTP_500_INTERNAL_SERVER_ERROR,
            HttpResponseBlob(error_code="code", error_message="error"),
        )

    return payer


@router.get("/api/v1/payers/{payer_id}")
async def get_payer(payer_id: str) -> JSONResponse:

    logger.info("get_payer() payer_id=%s", payer_id)

    return create_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        HttpResponseBlob(error_code="code", error_message="error"),
    )


@router.patch("/api/v1/payers/{payer_id}")
async def update_payer(payer_id: str) -> JSONResponse:

    logger.info("update_payer() payer_id=%s", payer_id)

    return create_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        HttpResponseBlob(error_code="code", error_message="error"),
    )


def create_response_blob(status_code: int, resp_blob: BaseModel):
    return JSONResponse(status_code=status_code, content=jsonable_encoder(resp_blob))
