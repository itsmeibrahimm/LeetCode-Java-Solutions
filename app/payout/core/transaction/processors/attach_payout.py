from structlog.stdlib import BoundLogger
from typing import Union, List, Optional

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.exceptions import transaction_invalid
from app.payout.core.transaction.types import (
    TransactionInternal,
    TransactionListInternal,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout import types
import app.payout.core.transaction.utils as utils

ERROR_MSG_INPUT_CONTAIN_INVALID_TRANSACTION = "The input transaction ids contain invalid transaction which is not allowed to attach to payout id."
ERROR_MSG_TRANSACTION_HAS_TRANSFER_ID_CANNOT_BE_ATTACHED_TO_PAYOUT_ID = (
    "Attach payout_id to a transaction with a transfer_id is not allowed."
)


class AttachPayoutRequest(OperationRequest):
    transaction_ids: List[types.TransactionId]
    payout_id: Optional[types.PayoutId] = None


class AttachPayout(AsyncOperation[AttachPayoutRequest, TransactionListInternal]):
    """
    Processor to attach a payout_id to a list of transactions
    """

    transaction_repo: TransactionRepositoryInterface

    def __init__(
        self,
        request: AttachPayoutRequest,
        *,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.transaction_repo = transaction_repo

    async def _execute(self) -> TransactionListInternal:
        # validate transaction_ids
        transactions = await self.transaction_repo.get_transaction_by_ids(
            self.request.transaction_ids
        )
        if len(transactions) != len(self.request.transaction_ids):
            raise transaction_invalid(ERROR_MSG_INPUT_CONTAIN_INVALID_TRANSACTION)
        for transaction in transactions:
            if transaction and transaction.transfer_id:
                raise transaction_invalid(
                    ERROR_MSG_TRANSACTION_HAS_TRANSFER_ID_CANNOT_BE_ATTACHED_TO_PAYOUT_ID
                )

        updated_transactions = await self.transaction_repo.set_transaction_payout_id_by_ids(
            transaction_ids=self.request.transaction_ids,
            payout_id=self.request.payout_id,
        )
        transaction_internal_list: List[TransactionInternal] = [
            utils.to_transaction_internal(transaction)
            for transaction in updated_transactions
        ]
        return TransactionListInternal(
            data=transaction_internal_list, count=len(transaction_internal_list)
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, TransactionListInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
