from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_404_NOT_FOUND,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError, MarqetaErrorCode
from app.purchasecard.api.card.v0.models import (
    AssociateMarqetaCardResponse,
    AssociateMarqetaCardRequest,
    UnassociateMarqetaCardResponse,
    UnassociateMarqetaCardRequest,
    GetMarqetaCardRequest,
    GetMarqetaCardResponse,
)
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.card.models import (
    InternalAssociateCardResponse,
    InternalUnassociateCardResponse,
    InternalGetMarqetaCardResponse,
)
from app.purchasecard.core.card.processor import CardProcessor

api_tags = ["CardsV0"]
router = APIRouter()


@router.post(
    "/associate_marqeta",
    status_code=HTTP_200_OK,
    operation_id="AssociateMarqetaCardWithUser",
    response_model=AssociateMarqetaCardResponse,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def associate_marqeta_card_with_user(
    request: AssociateMarqetaCardRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        card_processor: CardProcessor = dependency_container.card_processor
        response: InternalAssociateCardResponse = await card_processor.associate_card_with_dasher(
            delight_number=request.delight_number,
            last4=request.last4,
            dasher_id=request.dasher_id,
            user_token=request.user_token,
            is_dispatcher=request.is_dispatcher,
        )
        return AssociateMarqetaCardResponse(
            old_card_relinquished=response.old_card_relinquished,
            num_prev_owners=response.num_prev_owners,
        )
    except PaymentError as e:
        if e.error_code in (
            MarqetaErrorCode.MARQETA_CANNOT_ASSIGN_CARD_ERROR,
            MarqetaErrorCode.MARQETA_CANNOT_MOVE_CARD_TO_NEW_CARDHOLDER_ERROR,
        ):
            status = HTTP_400_BAD_REQUEST
        else:
            status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )


@router.post(
    "/unassociate_marqeta",
    status_code=HTTP_200_OK,
    operation_id="UnassociateMarqetaCardWithUser",
    response_model=UnassociateMarqetaCardResponse,
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def unassociate_marqeta_from_user(
    request: UnassociateMarqetaCardRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        card_processor: CardProcessor = dependency_container.card_processor
        response: InternalUnassociateCardResponse = await card_processor.unassociate_card_from_dasher(
            dasher_id=request.dasher_id
        )

        return UnassociateMarqetaCardResponse(token=response.token)
    except PaymentError as e:
        if (
            e.error_code
            == MarqetaErrorCode.MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR
        ):
            status = HTTP_404_NOT_FOUND
        else:
            status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )


@router.get(
    "/{dasher_id}",
    status_code=HTTP_200_OK,
    operation_id="GetMarqetaCardByDasherId",
    responses={
        HTTP_404_NOT_FOUND: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_marqeta_card_by_dasher_id(
    request: GetMarqetaCardRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        card_processor: CardProcessor = dependency_container.card_processor
        response: InternalGetMarqetaCardResponse = await card_processor.get_marqeta_card_by_dasher_id(
            dasher_id=request.dasher_id
        )
        return GetMarqetaCardResponse(
            token=response.token,
            delight_number=response.delight_number,
            terminated_at=response.terminated_at,
            last4=response.last4,
        )
    except PaymentError as e:
        if e.error_code in (
            MarqetaErrorCode.MARQETA_NO_ACTIVE_CARD_OWNERSHIP_DASHER_ERROR,
            MarqetaErrorCode.MARQETA_NO_CARD_FOUND_FOR_TOKEN_ERROR,
        ):
            status = HTTP_404_NOT_FOUND
        else:
            status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
