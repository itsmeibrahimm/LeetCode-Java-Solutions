from starlette.status import HTTP_200_OK
from fastapi import APIRouter, Path


api_tags = ["InstantPayoutsV1"]
router = APIRouter()


@router.post(
    "/{payout_account_id}/submit",
    operation_id="SubmitInstantPayout",
    status_code=HTTP_200_OK,
    tags=api_tags,
)
async def submit_instant_payout(
    payout_account_id: int = Path(..., description="Payout Account ID")
):
    ...
