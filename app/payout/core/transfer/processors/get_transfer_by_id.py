from starlette.status import HTTP_404_NOT_FOUND

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union, Optional
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.models import TransferId
from app.payout.repository.maindb.model.transfer import Transfer
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class GetTransferByIdResponse(OperationResponse):
    transfer: Optional[Transfer]


class GetTransferByIdRequest(OperationRequest):
    transfer_id: TransferId


class GetTransferById(AsyncOperation[GetTransferByIdRequest, GetTransferByIdResponse]):
    """
    Processor to get a transfer with given id.
    """

    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        request: GetTransferByIdRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo

    async def _execute(self) -> GetTransferByIdResponse:
        transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=self.request.transfer_id
        )
        if not transfer:
            raise PayoutError(
                http_status_code=HTTP_404_NOT_FOUND,
                error_code=PayoutErrorCode.TRANSFER_NOT_FOUND,
                retryable=False,
            )
        return GetTransferByIdResponse(transfer=transfer)

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, GetTransferByIdResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
