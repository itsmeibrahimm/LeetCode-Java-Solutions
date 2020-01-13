from fastapi import APIRouter, Depends
from starlette.status import (
    HTTP_200_OK,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.commons.api.models import PaymentErrorResponseBody, PaymentException
from app.commons.core.errors import PaymentError
from app.purchasecard.api.transaction.v0.models import (
    FundableAmountResponse,
    FundedAmountResponse,
    HasAssociatedMarqetaTransactionResponse,
)
from app.purchasecard.container import PurchaseCardContainer
from app.purchasecard.core.errors import INPUT_PARAM_INVALID_ERROR_CODE

api_tags = ["TransactionV0"]
router = APIRouter()


@router.get(
    "/fundable_amount/{delivery_id}",
    status_code=HTTP_200_OK,
    operation_id="FundableAmountByDelivery",
    response_model=FundableAmountResponse,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_fundable_amount_by_delivery(
    delivery_id: str,
    restaurant_total: int,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
) -> FundableAmountResponse:
    try:
        fundable_amount: int = await dependency_container.transaction_processor.get_fundable_amount_by_delivery_id(
            delivery_id=delivery_id, restaurant_total=restaurant_total
        )
        return FundableAmountResponse(fundable_amount=fundable_amount)
    except PaymentError as e:
        if e.error_code == INPUT_PARAM_INVALID_ERROR_CODE:
            status_code = HTTP_400_BAD_REQUEST
        else:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )


@router.get(
    "/funded_amount/{delivery_id}",
    status_code=HTTP_200_OK,
    operation_id="FundedAmountByDelivery",
    response_model=FundedAmountResponse,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def get_funded_amount_by_delivery(
    delivery_id: str,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
) -> FundedAmountResponse:
    try:
        funded_amount: int = await dependency_container.transaction_processor.get_funded_amount_by_delivery_id(
            delivery_id
        )
        return FundedAmountResponse(funded_amount=funded_amount)
    except PaymentError as e:
        if e.error_code == INPUT_PARAM_INVALID_ERROR_CODE:
            status_code = HTTP_400_BAD_REQUEST
        else:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )


@router.get(
    "/associated/{delivery_id}/",
    status_code=HTTP_200_OK,
    operation_id="HasAssociatedMarqetaTransaction",
    response_model=HasAssociatedMarqetaTransactionResponse,
    responses={
        HTTP_400_BAD_REQUEST: {"model": PaymentErrorResponseBody},
        HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody},
    },
    tags=api_tags,
)
async def has_associated_marqeta_transaction(
    delivery_id: str,
    ignore_timed_out: bool,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
) -> HasAssociatedMarqetaTransactionResponse:
    try:
        result: bool = await dependency_container.transaction_processor.has_associated_marqeta_transaction(
            delivery_id=delivery_id, ignore_timed_out=ignore_timed_out
        )
        return HasAssociatedMarqetaTransactionResponse(has_marqeta_transaction=result)
    except PaymentError as e:
        if e.error_code == INPUT_PARAM_INVALID_ERROR_CODE:
            status_code = HTTP_400_BAD_REQUEST
        else:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
        raise PaymentException(
            http_status_code=status_code,
            error_code=e.error_code,
            error_message=e.error_message,
            retryable=e.retryable,
        )
