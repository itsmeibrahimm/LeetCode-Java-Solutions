from fastapi import APIRouter, Depends
from starlette.status import HTTP_200_OK, HTTP_500_INTERNAL_SERVER_ERROR
from app.commons.providers.stripe.stripe_models import TransferId
from app.commons.api.models import PaymentErrorResponseBody
from app.payout.api.account.v1 import models
from app.payout.api.transfer.v1.models import SubmitTransfer
from app.payout.core.transfer.processor import TransferProcessors
from app.payout.core.transfer.processors.submit_transfer import SubmitTransferRequest
from app.payout.service import create_transfer_processors


api_tags = ["TransfersV1"]
router = APIRouter()


@router.post(
    "/{transfer_id}/submit",
    operation_id="SubmitTransfer",
    status_code=HTTP_200_OK,
    responses={HTTP_500_INTERNAL_SERVER_ERROR: {"model": PaymentErrorResponseBody}},
    tags=api_tags,
)
async def submit_transfer(
    transfer_id: TransferId,
    body: SubmitTransfer,
    transfer_processors: TransferProcessors = Depends(create_transfer_processors),
):
    submit_transfer_request = SubmitTransferRequest(
        transfer_id=transfer_id, retry=body.retry, submitted_by=body.submitted_by
    )
    submit_transfer_response = await transfer_processors.submit_transfer(
        submit_transfer_request
    )
    return models.Payout(**submit_transfer_response.dict())
