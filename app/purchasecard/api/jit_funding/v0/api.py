from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK

from app.purchasecard.api.jit_funding.v0.models import (
    JITFunding,
    MarqetaJITFundingResponse,
    MarqetaJITFundingRequest,
)
from app.purchasecard.container import PurchaseCardContainer

api_tags = ["JitFundingV0"]
router = APIRouter()


@router.post(
    "",
    status_code=HTTP_200_OK,
    operation_id="MarqetaJitFunding",
    response_model=MarqetaJITFundingResponse,
    tags=api_tags,
)
def marqeta_webhook(
    request: MarqetaJITFundingRequest,
    dependency_container: PurchaseCardContainer = Depends(PurchaseCardContainer),
):
    jit_funding: JITFunding = request.gpa_order.jit_funding
    return MarqetaJITFundingResponse(jit_funding=jit_funding)
