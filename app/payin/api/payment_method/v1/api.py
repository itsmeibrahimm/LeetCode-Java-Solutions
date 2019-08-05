import logging

from fastapi import APIRouter

from app.commons.error.errors import (
    PaymentErrorResponseBody,
    create_payment_error_response_blob,
)
from app.payin.api.payment_method.v1.request import CreatePaymentMethodRequest

from starlette.status import HTTP_201_CREATED, HTTP_200_OK, HTTP_501_NOT_IMPLEMENTED

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/api/v1/payment_methods", status_code=HTTP_201_CREATED)
async def create_payment_method(req_body: CreatePaymentMethodRequest):
    """
    Create a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id.
    - **payment_gateway**: [string] external payment gateway provider name.
    - **token**: [string] Token from external PSP to collect sensitive card or bank account
                 details, or personally identifiable information (PII), directly from your customers.
    - **legacy_payment_info**: [json object] legacy information for DSJ backward compatibility.
    - **consumer_id**: [string][in legacy_payment_info] DoorDash consumer id.
    - **stripe_customer_id**: [string][in legacy_payment_info] Stripe customer id.
    """
    logger.info(
        "[create_payment_method] receive request. payer_id:%s", req_body.payer_id
    )

    return create_payment_error_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        PaymentErrorResponseBody(
            error_code="not implemented",
            error_message="not implemented",
            retryable=False,
        ),
    )


@router.get(
    "/api/v1/payment_methods/{payer_id}/{payment_method_id}", status_code=HTTP_200_OK
)
async def get_payment_method(
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
):
    logger.info("[get_payment_method] receive request")

    return create_payment_error_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        PaymentErrorResponseBody(
            error_code="not implemented",
            error_message="not implemented",
            retryable=False,
        ),
    )


@router.get("/api/v1/payment_methods", status_code=HTTP_200_OK)
async def list_payment_methods(
    payer_id: str = None,
    payment_method_id: str = None,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
):
    logger.info("[list_payment_method] receive request")

    return create_payment_error_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        PaymentErrorResponseBody(
            error_code="not implemented",
            error_message="not implemented",
            retryable=False,
        ),
    )


@router.delete(
    "/api/v1/payment_methods/{payer_id}/{payment_method_id}", status_code=HTTP_200_OK
)
async def delete_payment_method(
    payer_id: str,
    payment_method_id: str,
    payer_type: str = None,
    payment_method_object_type: str = None,
):
    logger.info("[create_payment_method] receive request")

    return create_payment_error_response_blob(
        HTTP_501_NOT_IMPLEMENTED,
        PaymentErrorResponseBody(
            error_code="not implemented",
            error_message="not implemented",
            retryable=False,
        ),
    )
