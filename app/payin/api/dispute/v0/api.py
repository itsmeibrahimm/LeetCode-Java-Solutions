from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query
from starlette.status import HTTP_200_OK
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.types import CountryCode
from app.payin.core.dispute.model import (
    Dispute,
    DisputeChargeMetadata,
    DisputeList,
    Evidence,
)
from app.payin.core.dispute.processor import DisputeProcessor
from app.payin.core.dispute.types import DisputeIdType, ReasonType
from app.payin.core.exceptions import PayinError, PayinErrorCode

api_tags = ["DisputeV0"]
router = APIRouter()


@router.get(
    "/disputes/{dd_stripe_dispute_id}",
    response_model=Dispute,
    status_code=HTTP_200_OK,
    operation_id="GetDispute",
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
    dispute = await dispute_processor.get_dispute(
        dd_stripe_dispute_id=dd_stripe_dispute_id
    )
    log.info("[get_dispute] completed", dd_stripe_dispute_id=dd_stripe_dispute_id)
    return dispute


@router.post(
    "/disputes/{stripe_dispute_id}/submit",
    response_model=Dispute,
    status_code=HTTP_200_OK,
    operation_id="SubmitDisputeEvidence",
    tags=api_tags,
)
async def submit_dispute_evidence(
    stripe_dispute_id: str,
    evidence: Evidence,
    country: CountryCode = CountryCode.US,
    log: BoundLogger = Depends(get_logger_from_req),
    dispute_processor: DisputeProcessor = Depends(DisputeProcessor),
) -> Dispute:
    log.info("[update_dispute] update_dispute started", dispute_id=stripe_dispute_id)
    dispute = await dispute_processor.submit_dispute_evidence(
        stripe_dispute_id=stripe_dispute_id, evidence=evidence, country=country
    )
    log.info("[update_dispute] update_dispute completed", dispute_id=stripe_dispute_id)
    return dispute


@router.get(
    "/disputes",
    response_model=DisputeList,
    status_code=HTTP_200_OK,
    operation_id="ListDisputes",
    tags=api_tags,
)
async def list_disputes(
    dd_payment_method_id: str = None,
    stripe_payment_method_id: str = None,
    dd_stripe_card_id: int = None,
    dd_consumer_id: int = None,
    start_time: datetime = None,
    reasons: List[ReasonType] = Query([key.value for key in ReasonType]),
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
    - **reasons**: List[ReasonType] List of reasons for dispute. Default value considers all the reasons mentioned
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
        raise PayinError(
            error_code=PayinErrorCode.DISPUTE_LIST_MORE_THAN_ID_ONE_PARAMETER
        )
    elif parameter_count == 0:
        raise PayinError(error_code=PayinErrorCode.DISPUTE_LIST_NO_ID_PARAMETERS)
    log.info(
        "[list_disputes] list disputes started",
        payment_method_id=dd_payment_method_id,
        stripe_payment_method_id=stripe_payment_method_id,
        stripe_card_id=dd_stripe_card_id,
        dd_consumer_id=dd_consumer_id,
        start_time=start_time,
        reasons=reasons,
        distinct=distinct,
    )
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
    return dispute_list


@router.get(
    "/disputes/charge_metadata/{dispute_id_type}/{dispute_id}",
    response_model=DisputeChargeMetadata,
    status_code=HTTP_200_OK,
    operation_id="GetDisputeMetadata",
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
        "[get_dispute_charge_metadata] get_dispute_charge_metadata started",
        dispute_id=dispute_id,
        dispute_id_type=dispute_id_type,
    )
    dispute_charge_metadata: DisputeChargeMetadata = await dispute_processor.get_dispute_charge_metadata(
        dispute_id=dispute_id, dispute_id_type=dispute_id_type
    )
    log.info(
        "[get_dispute_charge_metadata] get_dispute_charge_metadata completed",
        dispute_id=dispute_id,
        dispute_id_type=dispute_id_type,
    )
    return dispute_charge_metadata
