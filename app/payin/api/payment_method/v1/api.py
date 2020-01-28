from typing import Optional, Tuple
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import Request
from starlette.status import HTTP_200_OK, HTTP_201_CREATED
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.core.errors import PaymentError
from app.commons.utils.validation import not_none
from app.payin.api.payer.v1.request import CreatePayerRequest
from app.payin.api.payment_method.v1.request import CreatePaymentMethodRequestV1
from app.payin.core.exceptions import PayinError, PayinErrorCode
from app.payin.core.payer.model import PayerCorrelationIds
from app.payin.core.payer.v1.processor import PayerProcessorV1
from app.payin.core.payment_method.model import (
    PaymentMethod,
    PaymentMethodList,
    RawPaymentMethod,
)
from app.payin.core.payment_method.processor import PaymentMethodProcessor
from app.payin.core.payment_method.types import PaymentMethodSortKey
from app.payin.core.types import PayerReferenceIdType, MixedUuidStrType

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
    payer_processor_v1: PayerProcessorV1 = Depends(PayerProcessorV1),
):
    """
    Create a payment method for payer on DoorDash payments platform

    - **payer_id**: [string] DoorDash payer id.
    - **payer_correlation_ids**: DoorDash external correlation id for Payer.
    - **payer_correlation_ids.payer_reference_id**: DoorDash external reference id for Payer.
    - **payer_correlation_ids.payer_reference_id_type**: type that specifies the role of payer.
    - **create_payer_request**: CreatePayerRequest for payer creation if payer does not exists
    - **payment_gateway**: [string] external payment gateway provider name.
    - **token**: [string] Token from external PSP to collect sensitive card or bank account
                 details, or personally identifiable information (PII), directly from your customers.
    - **set_default**: [bool] set as default payment method or not.
    - **is_scanned**: [bool] Internal use by DD Fraud team.
    - **param is_active**: [bool] mark as active or not. For fraud usage.
    """
    log.info("[create_payment_method] receive request", req_body=req_body)
    payer_correlation_ids: Optional[
        PayerCorrelationIds
    ] = req_body.payer_correlation_ids
    if req_body.create_payer_request:
        create_payer_request: CreatePayerRequest = req_body.create_payer_request
        _verify_correlation_ids(
            log=log,
            create_payer_request=create_payer_request,
            payer_correlation_ids=payer_correlation_ids,
        )
        payer, _ = await payer_processor_v1.create_payer(
            payer_reference_id=create_payer_request.payer_correlation_ids.payer_reference_id,
            payer_reference_id_type=create_payer_request.payer_correlation_ids.payer_reference_id_type,
            email=create_payer_request.email,
            country=create_payer_request.country,
            description=create_payer_request.description,
        )
        payer_correlation_ids = PayerCorrelationIds(
            payer_reference_id=not_none(payer.payer_correlation_ids).payer_reference_id,
            payer_reference_id_type=not_none(
                payer.payer_correlation_ids
            ).payer_reference_id_type,
        )
    payer_reference_ids: Tuple[
        MixedUuidStrType, PayerReferenceIdType
    ] = _parse_payer_reference_id_and_type(
        log=log,
        payer_id=req_body.payer_id,
        payer_reference_id=(
            payer_correlation_ids.payer_reference_id if payer_correlation_ids else None
        ),
        payer_reference_id_type=(
            payer_correlation_ids.payer_reference_id_type
            if payer_correlation_ids
            else None
        ),
    )

    try:
        raw_payment_method: RawPaymentMethod = await payment_method_processor.create_payment_method(
            payer_lookup_id=payer_reference_ids[0],
            payer_lookup_id_type=payer_reference_ids[1],
            pgp_code=req_body.payment_gateway,
            token=req_body.token,
            set_default=req_body.set_default,
            is_scanned=req_body.is_scanned,
            is_active=req_body.is_active,
        )
        external_payment_method: PaymentMethod = raw_payment_method.to_payment_method()
        log.info("[create_payment_method] completed.", payer_id=req_body.payer_id)
    except PaymentError:
        log.warn("[create_payment_method] PaymentError.", payer_id=req_body.payer_id)
        raise
    return external_payment_method


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
    active_only: Optional[bool],
    sort_by: Optional[PaymentMethodSortKey],
    force_update: Optional[bool],
    payer_id: Optional[UUID] = None,
    payer_reference_id: Optional[str] = None,
    payer_reference_id_type: Optional[PayerReferenceIdType] = None,
    log: BoundLogger = Depends(get_logger_from_req),
    payment_method_processor: PaymentMethodProcessor = Depends(PaymentMethodProcessor),
):
    log.info(
        "[list_payment_method] receive request",
        payer_id=payer_id,
        payer_reference_id_type=payer_reference_id_type,
        payer_reference_id=payer_reference_id,
        active_only=active_only,
        force_update=force_update,
        sort_by=sort_by,
    )

    payer_reference_ids: Tuple[
        MixedUuidStrType, PayerReferenceIdType
    ] = _parse_payer_reference_id_and_type(
        log=log,
        payer_id=payer_id,
        payer_reference_id=payer_reference_id,
        payer_reference_id_type=payer_reference_id_type,
    )

    payment_methods_list: PaymentMethodList
    try:
        payer_lookup_id: Optional[MixedUuidStrType] = payer_id or payer_reference_id
        if payer_lookup_id:
            payment_methods_list = await payment_method_processor.list_payment_methods(
                payer_lookup_id=payer_reference_ids[0],
                payer_reference_id_type=payer_reference_ids[1],
                active_only=active_only or False,
                sort_by=sort_by or PaymentMethodSortKey.CREATED_AT,
                force_update=force_update or False,
            )
    except PaymentError:
        log.warn("[list_payment_methods] PaymentError", payer_id=payer_id)
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


def _parse_payer_reference_id_and_type(
    log: BoundLogger,
    payer_id: Optional[UUID],
    payer_reference_id: Optional[str],
    payer_reference_id_type: Optional[PayerReferenceIdType],
) -> Tuple[MixedUuidStrType, PayerReferenceIdType]:
    if payer_id and not (payer_reference_id or payer_reference_id_type):
        return payer_id, PayerReferenceIdType.PAYER_ID
    elif (payer_reference_id and payer_reference_id_type) and not payer_id:
        return payer_reference_id, payer_reference_id_type
    else:
        log.warn(
            "[_parse_payer_reference_id_and_type] invalid input payer_id or payer_reference_id",
            payer_id=payer_id,
            payer_reference_id_type=payer_reference_id_type,
            payer_reference_id=payer_reference_id,
        )
        raise PayinError(
            error_code=PayinErrorCode.PAYMENT_METHOD_GET_INVALID_PAYER_REFERENCE_ID
        )


def _verify_correlation_ids(
    log: BoundLogger,
    create_payer_request: CreatePayerRequest,
    payer_correlation_ids: Optional[PayerCorrelationIds] = None,
):
    if payer_correlation_ids and (
        create_payer_request.payer_correlation_ids.payer_reference_id
        != payer_correlation_ids.payer_reference_id
        or create_payer_request.payer_correlation_ids.payer_reference_id_type
        != payer_correlation_ids.payer_reference_id_type
    ):
        log.error("[create_payment_method] Mismatch in correlation ids for payer")
        raise PayinError(
            error_code=PayinErrorCode.PAYMENT_METHOD_PAYER_CORRELATION_ID_MISMATCH
        )
