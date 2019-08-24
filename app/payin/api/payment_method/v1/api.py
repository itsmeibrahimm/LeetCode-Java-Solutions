from typing import Optional

from fastapi import APIRouter, Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.error.errors import PaymentError, PaymentException
from app.payin.api.payment_method.v1.request import CreatePaymentMethodRequest

from starlette.requests import Request

from starlette.status import (
    HTTP_201_CREATED,
    HTTP_200_OK,
    HTTP_501_NOT_IMPLEMENTED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
)

from app.payin.core.exceptions import PayinErrorCode
from app.payin.core.payment_method.model import PaymentMethod
from app.payin.core.payment_method.processor import PaymentMethodProcessor

router = APIRouter()


@router.post("/api/v1/payment_methods", status_code=HTTP_201_CREATED)
async def create_payment_method(
    request: Request,
    req_body: CreatePaymentMethodRequest,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Create a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id.
    - **payment_gateway**: [string] external payment gateway provider name.
    - **token**: [string] Token from external PSP to collect sensitive card or bank account
                 details, or personally identifiable information (PII), directly from your customers.
    - **legacy_payment_info**: [json object] legacy information for DSJ backward compatibility.
    - **dd_consumer_id**: [string][in legacy_payment_info] DoorDash consumer id.
    - **stripe_customer_id**: [string][in legacy_payment_info] Stripe customer id.
    """
    log.info("[create_payment_method] receive request. payer_id:%s", req_body.payer_id)

    dd_consumer_id: Optional[
        str
    ] = req_body.legacy_payment_info.dd_consumer_id if req_body.legacy_payment_info else None
    stripe_customer_id: Optional[
        str
    ] = req_body.legacy_payment_info.stripe_customer_id if req_body.legacy_payment_info else None
    try:
        payment_method: PaymentMethod = await payment_method_processor.create_payment_method(
            payer_id=req_body.payer_id,
            pgp_code=req_body.payment_gateway,
            token=req_body.token,
            dd_consumer_id=dd_consumer_id,
            stripe_customer_id=stripe_customer_id,
        )
        log.info(
            f"[create_payment_method][{req_body.payer_id}][{dd_consumer_id}][{stripe_customer_id}] completed."
        )
    except PaymentError as e:
        log.error(
            f"[create_payment_method][{req_body.payer_id}][{dd_consumer_id}][{stripe_customer_id}] PaymentError."
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
    "/api/v1/payment_methods/{payer_id}/{payment_method_id}", status_code=HTTP_200_OK
)
async def get_payment_method(
    request: Request,
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Get a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id. For backward compatibility, payer_id can be payer_id,
                    stripe_customer_id, or stripe_customer_serial_id
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
                             can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_payer_id",
                        "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
    - **payment_method_id_type**: [string] identify the type of payment_method_id. Valid values include
                                  "dd_payment_method_id", "stripe_payment_method_id", "stripe_card_serial_id"
                                  (default is "dd_payment_method_id")
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """

    log.info(
        "[get_payment_method] receive request: payer_id=%s, payment_method_id=%s, payer_id_type=%s, payment_method_id_type=%s, force_update=%s",
        payer_id,
        payment_method_id,
        payer_id_type,
        payment_method_id_type,
        force_update,
    )

    try:
        payment_method: PaymentMethod = await payment_method_processor.get_payment_method(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
            force_update=force_update,
        )
    except PaymentError as e:
        log.error(
            f"[create_payment_method][{payer_id}][{payment_method_id}] PaymentMethodReadError."
        )
        raise PaymentException(
            http_status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return payment_method


@router.get("/api/v1/payment_methods", status_code=HTTP_200_OK)
async def list_payment_methods(
    request: Request,
    payer_id: str = None,
    payment_method_id: str = None,
    payer_id_type: str = None,
    payment_method_object_type: str = None,
    force_update: bool = None,
    log: BoundLogger = Depends(get_logger_from_req),
):
    log.info("[list_payment_method] receive request")

    raise PaymentException(
        http_status_code=HTTP_501_NOT_IMPLEMENTED,
        error_code="not implemented",
        error_message="not implemented",
        retryable=False,
    )


@router.delete(
    "/api/v1/payment_methods/{payer_id}/{payment_method_id}", status_code=HTTP_200_OK
)
async def delete_payment_method(
    request: Request,
    payer_id: str,
    payment_method_id: str,
    payer_id_type: str = None,
    payment_method_id_type: str = None,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Detach a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id. For backward compatibility, payer_id can be payer_id,
                    stripe_customer_id, or stripe_customer_serial_id
    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id can
                             be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **payer_id_type**: [string] identify the type of payer_id. Valid values include "dd_payer_id",
                         "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
    - **payment_method_id_type**: [string] identify the type of payment_method_id. Valid values including
                                  "dd_payment_method_id", "stripe_payment_method_id", "stripe_card_serial_id"
                                  (default is "dd_payment_method_id")
    """

    try:
        payment_method: PaymentMethod = await payment_method_processor.delete_payment_method(
            payer_id=payer_id,
            payment_method_id=payment_method_id,
            payer_id_type=payer_id_type,
            payment_method_id_type=payment_method_id_type,
        )
    except PaymentError as e:
        log.error(
            f"[delete_payment_method][{payer_id}][{payment_method_id}] PaymentMethodReadError."
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
