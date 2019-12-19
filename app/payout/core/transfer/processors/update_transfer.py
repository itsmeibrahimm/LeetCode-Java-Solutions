from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from structlog.stdlib import BoundLogger
from typing import Union
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.models import TransferId
from app.payout.repository.maindb.model.transfer import Transfer, TransferUpdate
from app.payout.repository.maindb.transfer import TransferRepositoryInterface


class UpdateTransferResponse(OperationResponse):
    transfer: Transfer


class UpdateTransferRequest(OperationRequest):
    transfer_id: TransferId
    status: str


class UpdateTransfer(AsyncOperation[UpdateTransferRequest, UpdateTransferResponse]):
    """
    Processor to update a transfer with given id.
    """

    transfer_repo: TransferRepositoryInterface

    def __init__(
        self,
        request: UpdateTransferRequest,
        *,
        transfer_repo: TransferRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transfer_repo = transfer_repo

    async def _execute(self) -> UpdateTransferResponse:
        update_request = TransferUpdate(status=self.request.status)
        transfer = await self.transfer_repo.update_transfer_by_id(
            transfer_id=self.request.transfer_id, data=update_request
        )
        if not transfer:
            raise PayoutError(
                http_status_code=HTTP_400_BAD_REQUEST,
                error_code=PayoutErrorCode.TRANSFER_NOT_FOUND,
                retryable=False,
            )
        return UpdateTransferResponse(transfer=transfer)

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, UpdateTransferResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
