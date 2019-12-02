from datetime import datetime
from typing import Optional

import pytz
from starlette.status import HTTP_200_OK
from fastapi import APIRouter, Body, Path, Depends, Query

from app.commons.api.errors import BadRequestErrorCode, payment_error_message_maps
from app.commons.api.models import BadRequestError
from app.commons.api.streams import decode_stream_cursor, encode_stream_cursor
from app.payout.api.instant_payout.v1 import models
from app.payout.core.instant_payout.models import (
    EligibilityCheckRequest,
    CreateAndSubmitInstantPayoutRequest,
    GetPayoutStreamRequest,
)
from app.payout.core.instant_payout.processor import InstantPayoutProcessors
from app.payout.models import PayoutAccountId
from app.payout.service import create_instant_payout_processors

api_tags = ["InstantPayoutsV1"]
router = APIRouter()


@router.post(
    "/",
    status_code=HTTP_200_OK,
    operation_id="SubmitInstantPayout",
    response_model=models.InstantPayout,
    tags=api_tags,
)
async def submit_instant_payout(
    body: models.InstantPayoutCreate = Body(...),
    instant_payout_processors: InstantPayoutProcessors = Depends(
        create_instant_payout_processors
    ),
):
    internal_request = CreateAndSubmitInstantPayoutRequest(
        payout_account_id=body.payout_account_id,
        amount=body.amount,
        currency=body.currency,
        card=body.card,
    )
    internal_instant_payout_response = await instant_payout_processors.create_and_submit_instant_payout(
        request=internal_request
    )
    return models.InstantPayout(**internal_instant_payout_response.dict())


@router.get(
    "/{payout_account_id}/eligibility",
    status_code=HTTP_200_OK,
    operation_id="CheckInstantPayoutEligibility",
    response_model=models.PaymentEligibility,
    tags=api_tags,
)
async def check_instant_payout_eligibility(
    payout_account_id: PayoutAccountId = Path(..., description="Payout Account ID"),
    local_start_of_day: int = Query(
        default=...,
        description="Instant Payout entity's local start of today in timestamp",
    ),
    instant_payout_processors: InstantPayoutProcessors = Depends(
        create_instant_payout_processors
    ),
):
    # raise invalid request error if converting local_start_of_day overflows
    # todo: Leon, replace with processor layer error when refactoring errors.
    try:
        created_after = datetime.fromtimestamp(local_start_of_day / 1.0, tz=pytz.UTC)
    except (OverflowError, OSError) as e:
        raise BadRequestError(
            error_code=BadRequestErrorCode.INVALID_VALUE_ERROR,
            error_message=payment_error_message_maps[
                BadRequestErrorCode.INVALID_VALUE_ERROR
            ],
        ) from e

    internal_request = EligibilityCheckRequest(
        payout_account_id=payout_account_id, created_after=created_after
    )
    internal_response = await instant_payout_processors.check_instant_payout_eligibility(
        internal_request
    )
    return models.PaymentEligibility(**internal_response.dict())


@router.get(
    "/{payout_account_id}/payouts",
    operation_id="GetInstantPayoutStreamByPayoutAccountId",
    status_code=HTTP_200_OK,
    response_model=models.InstantPayoutStream,
    tags=api_tags,
)
async def get_instant_payout_stream_by_payout_account_id(
    payout_account_id: PayoutAccountId = Path(..., description="Payout Account ID"),
    limit: int = Query(default=10, description="Number of instant payouts to retrieve"),
    cursor: dict = Depends(decode_stream_cursor),
    instant_payout_processors: InstantPayoutProcessors = Depends(
        create_instant_payout_processors
    ),
):
    offset = cursor.get("offset", 0)

    internal_request = GetPayoutStreamRequest(
        payout_account_id=payout_account_id, limit=limit, offset=offset
    )

    internal_response = await instant_payout_processors.get_instant_payout_stream_by_payout_account_id(
        request=internal_request
    )
    next_cursor: Optional[dict] = None
    if internal_response.offset:
        next_cursor = {"offset": internal_response.offset}

    external_instant_payouts = [
        models.InstantPayoutStreamItem(**item.dict())
        for item in internal_response.instant_payouts
    ]

    return models.InstantPayoutStream(
        count=internal_response.count,
        cursor=encode_stream_cursor(next_cursor),
        instant_payouts=external_instant_payouts,
    )
