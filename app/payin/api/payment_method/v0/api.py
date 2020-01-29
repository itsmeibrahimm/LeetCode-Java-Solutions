from typing import Tuple, Union

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from starlette.responses import JSONResponse
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.commons.types import CountryCode, PgpCode
from app.payin.api.payment_method.v0.request import CreatePaymentMethodRequestV0
from app.payin.core.payment_method.model import PaymentMethod, PaymentMethodList
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import (
    LegacyPaymentMethodInfo,
    PaymentMethodSortKey,
)
from app.payin.core.types import PaymentMethodIdType

api_tags = ["PaymentMethodV0"]
router = APIRouter()


@router.post(
    "/payment_methods",
    response_model=PaymentMethod,
    status_code=HTTP_201_CREATED,
    operation_id="CreatePaymentMethod",
    tags=api_tags,
)
async def create_payment_method(
    req_body: CreatePaymentMethodRequestV0,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
) -> Union[JSONResponse, PaymentMethod]:
    """
    Create a payment method for payer on DoorDash payments platform

    - **token**: [string] Token from external PSP to collect sensitive card or bank account
                 details, or personally identifiable information (PII), directly from your customers.
    - **country**: [string] country code of DoorDash consumer
    - **dd_consumer_id**: [string] DoorDash consumer id.
    - **stripe_customer_id**: [string] Stripe customer id.
    - **payer_type**: [string] type that specifies the role of payer.
    - **set_default**: [bool] set as default payment method or not.
    - **is_scanned**: [bool] Internal use by DD Fraud team.
    - **param is_active**: [bool] mark as active or not. For fraud usage.
    """
    log.info("[create_payment_method] received request.", req_body=req_body)

    try:
        create_payment_method_result: Tuple[
            PaymentMethod, bool
        ] = await payment_method_processor.create_payment_method(
            pgp_code=PgpCode.STRIPE,
            token=req_body.token,
            set_default=req_body.set_default,
            is_scanned=req_body.is_scanned,
            is_active=req_body.is_active,
            legacy_payment_method_info=LegacyPaymentMethodInfo(
                dd_consumer_id=req_body.dd_consumer_id,
                legacy_dd_stripe_customer_id=req_body.legacy_dd_stripe_customer_id,
                stripe_customer_id=req_body.stripe_customer_id,
                country=req_body.country,
                payer_type=req_body.payer_type,
            ),
        )

        log.info(
            "[create_payment_method] completed.",
            stripe_customer_id=req_body.stripe_customer_id,
            payer_type=req_body.payer_type,
            dd_consumer_id=req_body.dd_consumer_id,
            legacy_dd_stripe_customer_id=req_body.legacy_dd_stripe_customer_id,
        )
    except PaymentError:
        log.exception(
            "[create_payment_method] PaymentError.",
            stripe_customer_id=req_body.stripe_customer_id,
            payer_type=req_body.payer_type,
            dd_consumer_id=req_body.dd_consumer_id,
            legacy_dd_stripe_customer_id=req_body.legacy_dd_stripe_customer_id,
        )
        raise
    payment_method, already_exists = create_payment_method_result
    if already_exists:
        return JSONResponse(
            status_code=HTTP_200_OK, content=jsonable_encoder(payment_method)
        )
    return payment_method


@router.get(
    "/payment_methods/{payment_method_id_type}/{payment_method_id}",
    response_model=PaymentMethod,
    status_code=HTTP_200_OK,
    operation_id="GetPaymentMethod",
    tags=api_tags,
)
async def get_payment_method(
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
        "[get_payment_method] received request",
        payment_method_id=payment_method_id,
        payment_method_id_type=payment_method_id_type,
    )

    try:
        payment_method: PaymentMethod = await payment_method_processor.get_payment_method(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
            country=country,
            force_update=force_update,
        )
    except PaymentError:
        log.warn(
            "[get_payment_method] PaymentMethodReadError.",
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )
        raise
    return payment_method


@router.get(
    "/payment_methods",
    response_model=PaymentMethodList,
    status_code=HTTP_200_OK,
    operation_id="ListPaymentMethods",
    tags=api_tags,
)
async def list_payment_methods(
    dd_consumer_id: str = None,
    stripe_customer_id: str = None,
    country: CountryCode = CountryCode.US,
    active_only: bool = False,
    sort_by: PaymentMethodSortKey = PaymentMethodSortKey.CREATED_AT,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    log.info(
        "[list_payment_method] receive request",
        dd_consumer_id=dd_consumer_id,
        stripe_customer_id=stripe_customer_id,
        country=country,
        active_only=active_only,
        force_update=force_update,
    )
    try:
        payment_method_list: PaymentMethodList = await payment_method_processor.list_payment_methods_legacy(
            dd_consumer_id=dd_consumer_id,
            stripe_customer_id=stripe_customer_id,
            country=country,
            active_only=active_only,
            sort_by=sort_by,
            force_update=force_update,
        )
    except PaymentError:
        log.warn("[list_payment_methods] PaymentError")
        raise
    return payment_method_list


@router.delete(
    "/payment_methods/{payment_method_id_type}/{payment_method_id}",
    response_model=PaymentMethod,
    status_code=HTTP_200_OK,
    operation_id="DeletePaymentMethod",
    tags=api_tags,
)
async def delete_payment_method(
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
    except PaymentError:
        log.exception(
            "[delete_payment_method] PaymentMethodReadError.",
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )
        raise

    return payment_method
