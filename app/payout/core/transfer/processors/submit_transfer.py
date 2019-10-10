from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.repository.maindb.transfer import TransferRepositoryInterface
from app.commons.providers.stripe import stripe_models as models


class SubmitTransferResponse(OperationResponse):
    pass


class SubmitTransferRequest(OperationRequest):
    transfer_id: models.TransferId
    retry: Optional[bool]
    submitted_by: Optional[int]


class SubmitTransfer(AsyncOperation[SubmitTransferRequest, SubmitTransferResponse]):
    """
    Processor to submit a transfer.
    """

    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        request: SubmitTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        stripe: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.stripe = stripe

    async def _execute(self) -> SubmitTransferResponse:
        self.logger.info("Submitting transfer", transfer_id=self.request.transfer_id)
        return SubmitTransferResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, SubmitTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
