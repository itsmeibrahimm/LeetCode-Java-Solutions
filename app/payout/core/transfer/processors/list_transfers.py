from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional, List
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.repository.maindb.model.transfer import Transfer
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class ListTransfersResponse(OperationResponse):
    count: int
    transfers: List[Transfer]


class ListTransfersRequest(OperationRequest):
    offset: int
    limit: int
    payment_account_ids: Optional[List[int]]


class ListTransfers(AsyncOperation[ListTransfersRequest, ListTransfersResponse]):
    """
    Processor to search transfers with given payment account ids.
    """

    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        request: ListTransfersRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo

    async def _execute(self) -> ListTransfersResponse:
        transfers: List[Transfer] = []
        count = 0
        offset = self.request.offset
        limit = self.request.limit
        if offset < 0 or limit < 0:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.INVALID_STRIPE_ACCOUNT,
                retryable=False,
            )
        if self.request.payment_account_ids:
            transfers, count = await self.transfer_repo.get_transfers_by_payment_account_ids_and_count(
                payment_account_ids=self.request.payment_account_ids,
                offset=offset,
                limit=limit,
            )
        return ListTransfersResponse(count=count, transfers=transfers)

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, ListTransfersResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
