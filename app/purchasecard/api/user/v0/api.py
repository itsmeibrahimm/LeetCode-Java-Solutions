from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_201_CREATED,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_409_CONFLICT,
)
from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError, MarqetaErrorCode
from app.purchasecard.api.user.v0.models import (
    CreateMarqetaUserRequest,
    CreateMarqetaUserResponse,
)
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.user.models import InternalMarqetaUser

api_tags = ["UsersV0"]
router = APIRouter()


@router.post(
    "/create_marqeta",
    status_code=HTTP_201_CREATED,
    operation_id="CreateMarqetaUser",
    response_model=CreateMarqetaUserResponse,
    responses={
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
        HTTP_409_CONFLICT: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def create_marqeta_user(
    request: CreateMarqetaUserRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    try:
        marqeta_user: InternalMarqetaUser = await dependency_container.user_processor.create_marqeta_user(
            token=request.token,
            first_name=request.first_name,
            last_name=request.last_name,
            email=request.email,
        )

        response = CreateMarqetaUserResponse(token=marqeta_user.token)
    except PaymentError as e:
        if e.error_code == MarqetaErrorCode.MARQETA_RESOURCE_ALREADY_CREATED_ERROR:
            status = HTTP_409_CONFLICT
        else:
            status = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
    return response
