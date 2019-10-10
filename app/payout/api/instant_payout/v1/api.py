from fastapi import APIRouter
from starlette.status import HTTP_200_OK


api_tags = ["InstantPayoutsV1"]
router = APIRouter()


@router.post(
    "/{payout_account_id}/submit",
    operation_id="SubmitInstantPayout",
    status_code=HTTP_200_OK,
    tags=api_tags,
)
async def submit_instant_payout():
    ...
