from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_400_BAD_REQUEST,
)
from structlog.stdlib import BoundLogger
from app.commons.types import CountryCode
from app.commons.api.models import PaymentErrorResponseBody
from app.commons.context.req_context import get_logger_from_req
from app.payout.api.account.utils import to_external_payout_account
from app.payout.core.account.processor import PayoutAccountProcessors
from app.payout.core.account.processors.create_account import CreatePayoutAccountRequest
from app.payout.core.account.processors.create_instant_payout import (
    CreateInstantPayoutRequest,
)
from app.payout.core.account.processors.create_payout_method import (
    CreatePayoutMethodRequest,
)
from app.payout.core.account.processors.create_standard_payout import (
    CreateStandardPayoutRequest,
)
from app.payout.core.account.processors.get_default_payout_card import (
    GetDefaultPayoutCardRequest,
)
from app.payout.core.account.processors.update_account_statement_descriptor import (
    UpdatePayoutAccountStatementDescriptorRequest,
)
from app.payout.core.account.processors.verify_account import VerifyPayoutAccountRequest
from app.payout.core.account.processors.get_account import GetPayoutAccountRequest
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.service import create_payout_account_processors
from app.payout.types import (
    PayoutAccountStatementDescriptor,
    PayoutType,
    PayoutTargetType,
    PayoutExternalAccountType,
)
from . import models

api_tags = ["AccountsV1"]
router = APIRouter()


@router.post(
    "/",
    status_code=HTTP_201_CREATED,
    operation_id="CreatePayoutAccount",
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def create_payout_account(
    body: models.CreatePayoutAccount,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
    log: BoundLogger = Depends(get_logger_from_req),
):

    log.debug(f"Creating payment_account for {body}.")
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
    payout_account_id: models.PayoutAccountId,
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
    payout_account_id: models.PayoutAccountId,
    statement_descriptor: PayoutAccountStatementDescriptor,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = UpdatePayoutAccountStatementDescriptorRequest(
        payout_account_id=payout_account_id, statement_descriptor=statement_descriptor
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
    payout_account_id: models.PayoutAccountId,
    verification_details: models.VerificationDetailsWithToken,
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
    operation_id="VerifyPayoutAccount",
    status_code=HTTP_200_OK,
    response_model=models.PayoutAccount,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def verify_payout_account(
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
    payout_account_id: models.PayoutAccountId,
    request: models.CreatePayoutMethod,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_request = CreatePayoutMethodRequest(
        payout_account_id=payout_account_id, token=request.token, type=request.type
    )
    internal_response = await payout_account_processors.create_payout_method(
        internal_request
    )
    return models.PayoutMethodCard(
        **internal_response.dict(), type=PayoutExternalAccountType.CARD
    )


@router.post(
    "/{payout_account_id}/payouts",
    operation_id="CreatePayout",
    status_code=HTTP_200_OK,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_payout(
    payout_account_id: models.PayoutAccountId,
    body: models.PayoutRequest,
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


@router.get(
    "/onboarding_required_fields/{entity_type}/{country_shortname}",
    status_code=HTTP_200_OK,
    operation_id="GetOnboardingRequirementsByStages",
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def get_onboarding_requirements_by_stages(
    entity_type: PayoutTargetType,
    country_shortname: CountryCode,
    payout_account_processors: PayoutAccountProcessors = Depends(
        create_payout_account_processors
    ),
):
    internal_onboarding_requirements = await payout_account_processors.get_onboarding_requirements_by_stages(
        entity_type=entity_type, country_shortname=country_shortname
    )
    return internal_onboarding_requirements
