from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

from app.purchasecard.api.transaction.v0.models import (
    FundableAmountResponse,
    FundedAmountResponse,
)
from app.purchasecard.container import PurchaseCardContainer

api_tags = ["TransactionV0"]
router = APIRouter()


@router.get(
    "/fundable_amount/{delivery_id}",
    status_code=HTTP_200_OK,
    operation_id="FundableAmountByDelivery",
    response_model=FundableAmountResponse,
    tags=api_tags,
)
async def get_fundable_amount_by_delivery(
    delivery_id: str,
    restaurant_total: int,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
) -> FundableAmountResponse:
    fundable_amount: int = await dependency_container.transaction_processor.get_fundable_amount_by_delivery_id(
        delivery_id=delivery_id, restaurant_total=restaurant_total
    )
    return FundableAmountResponse(fundable_amount=fundable_amount)


@router.get(
    "/funded_amount/{delivery_id}",
    status_code=HTTP_200_OK,
    operation_id="FundedAmountByDelivery",
    response_model=FundedAmountResponse,
    tags=api_tags,
)
async def get_funded_amount_by_delivery(
    delivery_id: str,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
) -> FundedAmountResponse:
    funded_amount: int = await dependency_container.transaction_processor.get_funded_amount_by_delivery_id(
        delivery_id
    )
    return FundedAmountResponse(funded_amount=funded_amount)
