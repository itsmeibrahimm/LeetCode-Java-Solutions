from datetime import datetime

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional, List
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.repository.maindb.transfer import TransferRepositoryInterface
from app.payout.types import PayoutTargetType, PayoutDay


class CreateTransferResponse(OperationResponse):
    pass


class CreateTransferRequest(OperationRequest):
    payout_account_id: int
    transfer_type: str
    bank_info_recently_changed: bool
    end_time: datetime
    start_time: Optional[datetime]
    target_id: Optional[int]
    target_type: Optional[PayoutTargetType]
    target_business_id: Optional[int]
    payout_day: Optional[PayoutDay]
    payout_countries: Optional[List[str]]


class CreateTransfer(AsyncOperation[CreateTransferRequest, CreateTransferResponse]):
    """
    Processor to create a transfer.
    """

    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        request: CreateTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo

    async def _execute(self) -> CreateTransferResponse:
        self.logger.info(
            "Creating transfer for payment account.",
            payment_account_id=self.request.payout_account_id,
        )
        return CreateTransferResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, CreateTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
