import logging
from typing import Optional

from fastapi import APIRouter

from app.commons.error.errors import (
    PaymentErrorResponseBody,
    create_payment_error_response_blob,
)
from app.payin.api.payment_method.v1.request import CreatePaymentMethodRequest

from starlette.status import (
    HTTP_201_CREATED,
    HTTP_200_OK,
    HTTP_501_NOT_IMPLEMENTED,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.payin.core.exceptions import PaymentMethodReadError, PaymentMethodCreateError
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.processor import (
    create_payment_method_impl,
    get_payment_method_impl,
)

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

    dd_consumer_id: Optional[
        str
    ] = req_body.legacy_payment_info.dd_consumer_id if req_body.legacy_payment_info else None
    stripe_customer_id: Optional[
        str
    ] = req_body.legacy_payment_info.stripe_customer_id if req_body.legacy_payment_info else None
    try:
        payment_method: PaymentMethod = await create_payment_method_impl(
            payer_id=req_body.payer_id,
            payment_gateway=req_body.payment_gateway,
            token=req_body.token,
            dd_consumer_id=dd_consumer_id,
            stripe_customer_id=stripe_customer_id,
        )
        logger.info(
            "[create_payment_method][%s][%s][%s] completed.",
            req_body.payer_id,
            dd_consumer_id,
            stripe_customer_id,
        )
    except PaymentMethodCreateError as e:
        logger.error(
            "[create_payment_method][{}][{}][{}] exception.".format(
                req_body.payer_id, dd_consumer_id, stripe_customer_id
            ),
            e,
        )
        return create_payment_error_response_blob(
            HTTP_500_INTERNAL_SERVER_ERROR,
            PaymentErrorResponseBody(
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            ),
        )
    return payment_method


@router.get(
    "/api/v1/payment_methods/{payer_id}/{payment_method_id}", status_code=HTTP_200_OK
)
async def get_payment_method(
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
    force_update: bool = None,
):
    """
    Get a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id. For backward compatibility, payer_id can be payer_id, stripe_customer_id, or stripe_customer_serial_id
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_payer_id", "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
    - **payment_method_id_type**: [string] identify the type of payment_method_id. Valid values include "dd_payment_method_id", "stripe_payment_method_id", "stripe_card_serial_id" (default is "dd_payment_method_id")
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """
    logger.info(
        "[get_payment_method] receive request: payer_id=%s, payment_method_id=%s, payer_id_type=%s, payment_method_id_type=%s, force_update=%s",
        payer_id,
        payment_method_id,
        payer_id_type,
        payment_method_id_type,
        force_update,
    )

    try:
        payment_method: PaymentMethod = await get_payment_method_impl(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
            force_update=force_update,
        )
    except PaymentMethodReadError as e:
        logger.error(
            "[create_payment_method][{}][{}] exception.".format(
                payer_id, payment_method_id
            ),
            e,
        )
        return create_payment_error_response_blob(
            HTTP_500_INTERNAL_SERVER_ERROR,
            PaymentErrorResponseBody(
                error_code=e.error_code,
                error_message=e.error_message,
                retryable=e.retryable,
            ),
        )
    return payment_method


@router.get("/api/v1/payment_methods", status_code=HTTP_200_OK)
async def list_payment_methods(
    payer_id: str = None,
    payment_method_id: str = None,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
    force_update: bool = None,
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
