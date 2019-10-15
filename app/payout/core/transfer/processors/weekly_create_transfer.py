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


class WeeklyCreateTransferResponse(OperationResponse):
    pass


class WeeklyCreateTransferRequest(OperationRequest):
    transfer_id: models.TransferId
    retry: Optional[bool]
    submitted_by: Optional[int]


class WeeklyCreateTransfer(
    AsyncOperation[WeeklyCreateTransferRequest, WeeklyCreateTransferResponse]
):
    """
    Processor to create a transfer when called by weekly_create_transfer in dsj.
    """

    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        request: WeeklyCreateTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        stripe: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo
        self.stripe = stripe

    async def _execute(self) -> WeeklyCreateTransferResponse:
        self.logger.info("Creating transfer, called by weekly_create_transfer.")
        return WeeklyCreateTransferResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, WeeklyCreateTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
