from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError, MarqetaErrorCode
from app.purchasecard.api.card.v0.models import (
    AssociateMarqetaCardResponse,
    AssociateMarqetaCardRequest,
)
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.card.models import InternalAssociateCardResponse

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
        response: InternalAssociateCardResponse = await dependency_container.card_processor.associate_card_with_dasher(
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
