from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.models import PaymentErrorResponseBody
from app.purchasecard.api.auth.v0.models import CreateAuthResponse, CreateAuthRequest
from app.purchasecard.container import PurchaseCardContainer

api_tags = ["AuthV0"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_200_OK,
    operation_id="CreateAuth",
    response_model=CreateAuthResponse,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_auth(
    request: CreateAuthRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    pass
