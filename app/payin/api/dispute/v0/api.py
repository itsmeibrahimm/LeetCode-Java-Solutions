from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
)
from structlog.stdlib import BoundLogger

from app.commons.api.models import PaymentException, PaymentErrorResponseBody
from app.commons.context.req_context import get_logger_from_req
from app.commons.types import CountryCode
from app.payin.core.dispute.model import Evidence, DisputeChargeMetadata
from app.commons.core.errors import PaymentError
from app.payin.core.dispute.model import Dispute, DisputeList
from app.payin.core.dispute.processor import DisputeProcessor
from app.payin.core.dispute.types import DisputeIdType
from app.payin.core.exceptions import PayinErrorCode

api_tags = ["DisputeV0"]
router = APIRouter()


@router.get(
    "/disputes/{dd_stripe_dispute_id}",
    response_model=Dispute,
    status_code=HTTP_200_OK,
    operation_id="GetDispute",
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_dispute(
    dd_stripe_dispute_id: str,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> Dispute:
    """
    Get dispute.
    - **dd_stripe_dispute_id**: id for dispute in dispute table
    """
    log.info("[get_dispute] started", dd_stripe_dispute_id=dd_stripe_dispute_id)
    try:
        dispute: Dispute = await dispute_processor.get_dispute(
            dd_stripe_dispute_id=dd_stripe_dispute_id
        )
        log.info("[get_dispute] completed", dd_stripe_dispute_id=dd_stripe_dispute_id)
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_404_NOT_FOUND
                if e.error_code == PayinErrorCode.DISPUTE_NOT_FOUND
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return dispute


@router.post(
    "/disputes/{stripe_dispute_id}/submit",
    response_model=Dispute,
    status_code=HTTP_200_OK,
    operation_id="SubmitDisputeEvidence",
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def submit_dispute_evidence(
    stripe_dispute_id: str,
    evidence: Evidence,
    country: CountryCode = CountryCode.US,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> Dispute:
    log.info(
        "[update_dispute] update_dispute started for dispute_id=%s", stripe_dispute_id
    )
    try:
        dispute: Dispute = await dispute_processor.submit_dispute_evidence(
            stripe_dispute_id=stripe_dispute_id, evidence=evidence, country=country
        )
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_404_NOT_FOUND
                if e.error_code == PayinErrorCode.DISPUTE_NOT_FOUND
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    log.info(
        "[update_dispute] update_dispute completed for dispute_id=%s", stripe_dispute_id
    )
    return dispute


@router.get(
    "/disputes",
    response_model=DisputeList,
    status_code=HTTP_200_OK,
    operation_id="ListDisputes",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def list_disputes(
    dd_payment_method_id: str = None,
    stripe_payment_method_id: str = None,
    dd_stripe_card_id: int = None,
    dd_consumer_id: int = None,
    start_time: datetime = None,
    reasons: List[str] = Query(None),
    distinct: bool = False,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> DisputeList:
    """
    List disputes.
    - **dd_payment_method_id**: [string] Doordash payment method id
    - **stripe_payment_method_id**: [string] Stripe payment method id
    - **dd_stripe_card_id**: [int] Primary key in Stripe Card table
    - **dd_consumer_id**: [int]: Primary key in Consumer table
    - **start_time**: [datetime] Start date for disputes.Default will be the epoch time
    - **reasons**: List[str] List of reasons for dispute. Default value considers all the reasons mentioned
                    on https://stripe.com/docs/api/disputes/object#dispute_object-reason
    - **distinct**: [bool] Gives count of distinct disputes according to charge id. Default to False
    """
    parameters = [
        dd_payment_method_id,
        stripe_payment_method_id,
        dd_stripe_card_id,
        dd_consumer_id,
    ]
    parameter_count = sum([1 if parameter else 0 for parameter in parameters])
    if parameter_count > 1:
        raise PaymentException(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayinErrorCode.DISPUTE_LIST_MORE_THAN_ID_ONE_PARAMETER,
            error_message="More than 1 id parameter provided. Please verify your input",
            retryable=False,
        )
    elif parameter_count == 0:
        raise PaymentException(
            http_status_code=HTTP_400_BAD_REQUEST,
            error_code=PayinErrorCode.DISPUTE_LIST_NO_ID_PARAMETERS,
            error_message="No id parameters provides. Please verify your input",
            retryable=False,
        )
    log.info(
        f"[list_disputes] list disputes started for payment_method_id: {dd_payment_method_id} "
        f"stripe_payment_method_id: {stripe_payment_method_id} stripe_card_id: {dd_stripe_card_id} "
        f"consumer_id: {dd_consumer_id}"
        f"start_time: {start_time} reasons: {reasons} distinct: {distinct}"
    )
    try:
        dispute_list = await dispute_processor.list_disputes(
            dd_payment_method_id=dd_payment_method_id,
            stripe_payment_method_id=stripe_payment_method_id,
            dd_stripe_card_id=dd_stripe_card_id,
            dd_consumer_id=dd_consumer_id,
            start_time=start_time,
            reasons=reasons,
            distinct=distinct,
        )
        log.info("[list_disputes] list_disputes completed")
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_400_BAD_REQUEST
                if e.error_code
                in (
                    PayinErrorCode.DISPUTE_READ_INVALID_DATA,
                    PayinErrorCode.DISPUTE_LIST_NO_PARAMETERS,
                )
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return dispute_list


@router.get(
    "/disputes/charge_metadata/{dispute_id_type}/{dispute_id}",
    response_model=DisputeChargeMetadata,
    status_code=HTTP_200_OK,
    operation_id="GetDisputeMetadata",
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_dispute_charge_metadata(
    dispute_id_type: DisputeIdType,
    dispute_id: str,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> DisputeChargeMetadata:
    """
    Get dispute charge metadata.
    - **dispute_id**: [string] id for dispute in dispute table
    - **dispute_id_type**: [string] identify the type of id for the dispute.
        Valid values include "dd_stripe_dispute_id" and "stripe_dispute_id"
    """
    log.info(
        f"[get_dispute_charge_metadata] get_dispute_charge_metadata started for dispute_id={dispute_id} dispute_id_type={dispute_id_type}"
    )
    try:
        dispute_charge_metadata: DisputeChargeMetadata = await dispute_processor.get_dispute_charge_metadata(
            dispute_id=dispute_id, dispute_id_type=dispute_id_type
        )
    except PaymentError as e:
        raise PaymentException(
            http_status_code=(
                HTTP_404_NOT_FOUND
                if e.error_code
                in (
                    PayinErrorCode.DISPUTE_NOT_FOUND,
                    PayinErrorCode.DISPUTE_NO_CONSUMER_CHARGE_FOR_STRIPE_DISPUTE,
                )
                else HTTP_500_INTERNAL_SERVER_ERROR
            ),
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    log.info(
        f"[get_dispute_charge_metadata] get_dispute_charge_metadata completed for dispute_id={dispute_id} dispute_id_type={dispute_id_type}"
    )
    return dispute_charge_metadata
