from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.payin.api.payment_method.v1.request import CreatePaymentMethodRequestV1
from app.payin.core.payment_method.model import PaymentMethod, PaymentMethodList
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import PaymentMethodSortKey

api_tags = ["PaymentMethodV1"]
router = APIRouter()


@router.post(
    "/payment_methods",
    response_model=PaymentMethod,
    status_code=HTTP_201_CREATED,
    operation_id="CreatePaymentMethod",
    tags=api_tags,
)
async def create_payment_method(
    req_body: CreatePaymentMethodRequestV1,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Create a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id.
    - **payment_gateway**: [string] external payment gateway provider name.
    - **token**: [string] Token from external PSP to collect sensitive card or bank account
                 details, or personally identifiable information (PII), directly from your customers.
    - **set_default**: [bool] set as default payment method or not.
    - **is_scanned**: [bool] Internal use by DD Fraud team.
    - **param is_active**: [bool] mark as active or not. For fraud usage.
    """
    log.info("[create_payment_method] receive request", req_body=req_body)

    try:
        payment_method: PaymentMethod = await payment_method_processor.create_payment_method(
            payer_id=req_body.payer_id,
            pgp_code=req_body.payment_gateway,
            token=req_body.token,
            set_default=req_body.set_default,
            is_scanned=req_body.is_scanned,
            is_active=req_body.is_active,
        )
        log.info("[create_payment_method] completed.", payer_id=req_body.payer_id)
    except PaymentError:
        log.warn("[create_payment_method] PaymentError.", payer_id=req_body.payer_id)
        raise
    return payment_method


@router.get(
    "/payment_methods/{payment_method_id}",
    response_model=PaymentMethod,
    status_code=HTTP_200_OK,
    operation_id="GetPaymentMethod",
    tags=api_tags,
)
async def get_payment_method(
    payment_method_id: str,
    force_update: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Get a payment method for payer on DoorDash payments platform

    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id
                             can be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    - **force_update**: [boolean] specify if requires a force update from Payment Provider (default is "false")
    """

    log.info(
        "[get_payment_method] receive request", payment_method_id=payment_method_id
    )

    try:
        payment_method: PaymentMethod = await payment_method_processor.get_payment_method(
            payment_method_id=payment_method_id, force_update=force_update
        )
    except PaymentError:
        log.warn(
            "[get_payment_method] PaymentMethodReadError.",
            payment_method_id=payment_method_id,
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
    request: Request,
    payer_id: str,
    active_only: bool = False,
    sort_by: PaymentMethodSortKey = PaymentMethodSortKey.CREATED_AT,
    force_update: bool = None,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    log.info(
        "[list_payment_method] receive request",
        payer_id=payer_id,
        active_only=active_only,
        force_update=force_update,
    )

    try:
        payment_methods_list: PaymentMethodList = await payment_method_processor.list_payment_methods(
            payer_id=payer_id,
            active_only=active_only,
            sort_by=sort_by,
            force_update=force_update,
        )
    except PaymentError:
        log.warn("[list_payment_methods] PaymentError")
        raise

    return payment_methods_list


@router.delete(
    "/payment_methods/{payment_method_id}",
    response_model=PaymentMethod,
    status_code=HTTP_200_OK,
    operation_id="DeletePaymentMethod",
    tags=api_tags,
)
async def delete_payment_method(
    request: Request,
    payment_method_id: str,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    """
    Detach a payment method for payer on DoorDash payments platform. If the detached payment method is the default
    one, DD payments platform will cleanup the Payer.default_payment_payment_method_id flag and it is client's
    responsibility to update the default payment method for invoice (Dashpass) use.

    - **payment_method_id**: [string] DoorDash payment method id. For backward compatibility, payment_method_id can
                             be either dd_payment_method_id, stripe_payment_method_id, or stripe_card_serial_id
    """

    try:
        payment_method: PaymentMethod = await payment_method_processor.delete_payment_method(
            payment_method_id=payment_method_id
        )
    except PaymentError:
        log.exception(
            "[delete_payment_method] PaymentMethodReadError.",
            payment_method_id=payment_method_id,
        )
        raise

    return payment_method
