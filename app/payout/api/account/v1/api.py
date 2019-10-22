from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
)
from structlog.stdlib import BoundLogger
from typing import Optional
from fastapi import APIRouter, Depends, Body, Path, Query

from app.commons.providers.stripe.stripe_models import TransferId
from app.commons.types import CountryCode
from app.commons.api.models import PaymentErrorResponseBody
from app.commons.api.streams import decode_stream_cursor, encode_stream_cursor
from app.commons.context.req_context import get_logger_from_req
from app.payout.api.account.utils import to_external_payout_account
from app.payout.api.account.v1 import models
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.core.transfer.cancel_payout import CancelPayoutRequest
from app.payout.core.account.processors.create_account import CreatePayoutAccountRequest
from app.payout.core.transfer.create_instant_payout import CreateInstantPayoutRequest
from app.payout.core.account.processors.create_payout_method import (
    CreatePayoutMethodRequest,
)
from app.payout.core.transfer.create_standard_payout import CreateStandardPayoutRequest
from app.payout.core.account.processors.get_account_stream import (
    GetPayoutAccountStreamRequest,
)
from app.payout.core.account.processors.get_default_payout_card import (
    GetDefaultPayoutCardRequest,
)
from app.payout.core.account.processors.get_payout_method import GetPayoutMethodRequest
from app.payout.core.account.processors.list_payout_methods import (
    ListPayoutMethodRequest,
)
from app.payout.core.account.processors.update_account_statement_descriptor import (
    UpdatePayoutAccountStatementDescriptorRequest,
)
from app.payout.core.account.processors.verify_account import VerifyPayoutAccountRequest
from app.payout.core.account.processors.get_account import GetPayoutAccountRequest
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.service import create_payout_account_processors
from app.payout.models import PayoutType, PayoutTargetType, PayoutExternalAccountType

api_tags = ["AccountsV1"]
router = APIRouter()


@router.get(
    "/",
    operation_id="GetPayoutAccountStream",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccountStream,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_payout_account_stream(
    log: BoundLogger = Depends(get_logger_from_req),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
    cursor: dict = Depends(decode_stream_cursor),
    limit: int = 10,
):
    log.info("getting payout account stream", extra={"cursor": cursor, "limit": limit})

    offset = cursor.get("offset", 0)
    request = GetPayoutAccountStreamRequest(offset=offset, limit=limit)

    stream = await payout_account_processors.get_payout_account_stream(request=request)

    items = [to_external_payout_account(account) for account in stream.items]

    next_cursor: Optional[dict] = None
    if stream.new_offset:
        next_cursor = {"offset": stream.new_offset}

    return models.PayoutAccountStream(
        cursor=encode_stream_cursor(next_cursor), items=items
    )


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayoutAccount",
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_payout_account(
    body: models.CreatePayoutAccount = Body(
        ..., description="Request body for creating a payout account"
    ),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
    log: BoundLogger = Depends(get_logger_from_req),
):
    log.debug("creating payment_account", extra=dict(body=body))
    internal_request = CreatePayoutAccountRequest(
        entity=body.target_type, statement_descriptor=body.statement_descriptor
    )
    internal_response = await payout_account_processors.create_payout_account(
        internal_request
    )
    external_response = to_external_payout_account(internal_response)
    return models.PayoutAccount(**external_response.dict())


@router.get(
    "/{payout_account_id}",
    status_code=HTTP_200_OK,
    operation_id="GetPayoutAccount",
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_payout_account(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = GetPayoutAccountRequest(payout_account_id=payout_account_id)
    internal_response = await payout_account_processors.get_payout_account(
        internal_request
    )
    external_response = to_external_payout_account(internal_response)
    return models.PayoutAccount(**external_response.dict())


@router.patch(
    "/{payout_account_id}/statement_descriptor",
    operation_id="UpdatePayoutAccountStatementDescriptor",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def update_payout_account_statement_descriptor(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    body: models.UpdatePayoutAccountStatementDescriptor = Body(
        ..., description="Statement descriptor for payouts"
    ),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = UpdatePayoutAccountStatementDescriptorRequest(
        payout_account_id=payout_account_id,
        statement_descriptor=body.dict().get("statement_descriptor"),
    )
    internal_response = await payout_account_processors.update_payout_account_statement_descriptor(
        internal_request
    )
    external_response = to_external_payout_account(internal_response)
    return models.PayoutAccount(**external_response.dict())


@router.post(
    "/{payout_account_id}/verify/legacy",
    operation_id="VerifyPayoutAccountLegacy",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def verify_payout_account_legacy(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    verification_details: models.VerificationDetailsWithToken = Body(
        ..., description="Verification details with token, country and currency"
    ),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = VerifyPayoutAccountRequest(
        payout_account_id=payout_account_id,
        country=verification_details.country,
        account_token=verification_details.account_token,
    )
    internal_response = await payout_account_processors.verify_payout_account(
        internal_request
    )
    external_response = to_external_payout_account(internal_response)
    return models.PayoutAccount(**external_response.dict())


@router.post(
    "/{payout_account_id}/verify",
    operation_id="VerifyPayoutAccountToBeImplemented",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def verify_payout_account_to_be_implemented(
    payout_account_id: models.PayoutAccountId,
    verification_details: models.VerificationDetailsWithToken,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    # accept account token generated by Stripe API 2019 version
    ...


@router.post(
    "/{payout_account_id}/payout_methods",
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayoutMethod",
    response_model=models.PayoutMethodCard,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_payout_method(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    payout_method: models.CreatePayoutMethod = Body(..., description="Payout Method"),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = CreatePayoutMethodRequest(
        payout_account_id=payout_account_id,
        token=payout_method.token,
        type=payout_method.type,
    )
    internal_response = await payout_account_processors.create_payout_method(
        internal_request
    )
    return models.PayoutMethodCard(
        **internal_response.dict(), type=PayoutExternalAccountType.CARD
    )


@router.get(
    "/{payout_account_id}/payout_methods/{payout_method_id}",
    status_code=HTTP_200_OK,
    operation_id="GetPayoutMethod",
    response_model=models.PayoutMethodCard,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_payout_method(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    payout_method_id: models.PayoutMethodId = Path(..., description="Payout Method ID"),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = GetPayoutMethodRequest(
        payout_account_id=payout_account_id, payout_method_id=payout_method_id
    )
    internal_response = await payout_account_processors.get_payout_method(
        internal_request
    )
    return models.PayoutMethodCard(
        **internal_response.dict(), type=PayoutExternalAccountType.CARD
    )


@router.get(
    "/{payout_account_id}/payout_methods",
    status_code=HTTP_200_OK,
    operation_id="ListPayoutMethod",
    response_model=models.PayoutMethodList,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def list_payout_method(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    payout_method_type: models.PayoutExternalAccountType = Query(
        default=PayoutExternalAccountType.CARD, description="Payout method type"
    ),
    limit: int = Query(default=50, description="Default limit of returned results"),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = ListPayoutMethodRequest(
        payout_account_id=payout_account_id,
        payout_method_type=payout_method_type,
        limit=limit,
    )
    internal_response = await payout_account_processors.list_payout_method(
        internal_request
    )

    # TODO: need to merge card and bank payout methods
    payout_method_card_list = []
    for card_internal in internal_response.data:
        payout_method_card_list.append(
            models.PayoutMethodCard(
                **card_internal.dict(), type=PayoutExternalAccountType.CARD
            )
        )
    return models.PayoutMethodList(
        card_list=payout_method_card_list, count=len(payout_method_card_list)
    )


@router.post(
    "/{payout_account_id}/payouts",
    operation_id="CreatePayout",
    status_code=HTTP_201_CREATED,
    response_model=models.Payout,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_payout(
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    body: models.PayoutRequest = Body(..., description="Create payout request body"),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    # The if-else check here is ok for now, since PayoutType only has "standard" and "instant"
    if body.payout_type == PayoutType.STANDARD:
        standard_payout_request = CreateStandardPayoutRequest(
            payout_account_id=payout_account_id,
            amount=body.amount,
            payout_type=body.payout_type,
            statement_descriptor=body.statement_descriptor,
            target_id=body.target_id,
            target_type=body.target_type,
            transfer_id=body.transfer_id,
            method=body.method,
            submitted_by=body.submitted_by,
        )
        standard_payout_response = await payout_account_processors.create_standard_payout(
            standard_payout_request
        )
        return models.Payout(**standard_payout_response.dict())
    else:
        retrieve_method_request = GetDefaultPayoutCardRequest(
            payout_account_id=payout_account_id
        )
        try:
            payout_card_method = await payout_account_processors.get_default_payout_card(
                retrieve_method_request
            )
            # todo: remove this after id of payout_card_method updated to required
            assert payout_card_method.id, "payout_card_method id is required"
        except Exception:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.DEFAULT_PAYOUT_CARD_NOT_FOUND,
                retryable=False,
            )

        payout_card_id = payout_card_method.id
        instant_payout_request = CreateInstantPayoutRequest(
            payout_account_id=payout_account_id,
            amount=body.amount,
            payout_type=body.payout_type,
            payout_id=body.payout_id,
            payout_card_id=payout_card_id,
            payout_stripe_card_id=payout_card_method.stripe_card_id,
            payout_idempotency_key=body.payout_idempotency_key,
            method=body.method,
            submitted_by=body.submitted_by,
        )
        instant_payout_response = await payout_account_processors.create_instant_payout(
            instant_payout_request
        )
        return models.Payout(**instant_payout_response.dict())


@router.post(
    "/{payout_account_id}/transfer/{transfer_id}/cancel",
    operation_id="CancelPayout",
    status_code=HTTP_200_OK,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def cancel_payout(
    transfer_id: TransferId = Path(..., description="Transfer ID"),
    payout_account_id: models.PayoutAccountId = Path(
        ..., description="Payout Account ID"
    ),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    cancel_payout_request = CancelPayoutRequest(
        transfer_id=transfer_id, payout_account_id=payout_account_id
    )
    cancel_payout_response = await payout_account_processors.cancel_payout(
        cancel_payout_request
    )
    return models.Payout(**cancel_payout_response.dict())


@router.get(
    "/onboarding_required_fields/",
    status_code=HTTP_200_OK,
    operation_id="GetOnboardingRequirementsByStages",
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_onboarding_requirements_by_stages(
    entity_type: PayoutTargetType = Query(..., description="Payout target type"),
    country_shortname: CountryCode = Query(..., description="Country shortname"),
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_onboarding_requirements = await payout_account_processors.get_onboarding_requirements_by_stages(
        entity_type=entity_type, country_shortname=country_shortname
    )
    return internal_onboarding_requirements
