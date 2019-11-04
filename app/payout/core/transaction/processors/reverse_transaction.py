import json

from structlog.stdlib import BoundLogger
from typing import Union, Optional

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.constants import TRANSACTION_REVERSAL_PREFIX
from app.payout.core.exceptions import transaction_invalid
from app.payout.core.transaction.models import TransactionInternal
from app.payout.repository.bankdb.model.transaction import TransactionCreateDBEntity
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout import models
import app.payout.core.transaction.utils as utils

ERROR_MSG_TRANSACTION_NOT_EXIST_FOR_REVERSE = (
    "Cannot find a transaction with the given transaction id for reverse."
)
ERROR_MSG_TRANSACTION_ALREADY_CANCELLED = (
    "Reverse a cancelled transaction is not allowed."
)


class ReverseTransactionRequest(OperationRequest):
    transaction_id: models.TransactionId
    reverse_reason: Optional[str]


class ReverseTransaction(
    AsyncOperation[ReverseTransactionRequest, TransactionInternal]
):
    """
    Processor to reverse a transaction
    """

    transaction_repo: TransactionRepositoryInterface

    def __init__(
        self,
        request: ReverseTransactionRequest,
        *,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.transaction_repo = transaction_repo

    async def _execute(self) -> TransactionInternal:
        # get the transaction to reverse
        transaction = await self.transaction_repo.get_transaction_by_id(
            self.request.transaction_id
        )
        if not transaction:
            raise transaction_invalid(ERROR_MSG_TRANSACTION_NOT_EXIST_FOR_REVERSE)
        if transaction.state == models.TransactionState.CANCELLED.value:
            raise transaction_invalid(ERROR_MSG_TRANSACTION_ALREADY_CANCELLED)

        # create a negative transaction for the original one
        reversed_transaction = await self.transaction_repo.create_transaction(
            TransactionCreateDBEntity(
                payment_account_id=transaction.payment_account_id,
                amount=transaction.amount * -1,  # negative amount
                amount_paid=transaction.amount_paid * -1,
                metadata=json.dumps(
                    ReverseTransaction.metadata_for_reversal(
                        self.request.transaction_id, self.request.reverse_reason
                    )
                ),
                idempotency_key=ReverseTransaction.idempotency_key_for_reversal(
                    self.request.transaction_id
                ),
                currency=transaction.currency,
                target_id=transaction.target_id,
                target_type=transaction.target_type,
            )
        )
        return utils.get_transaction_internal_from_db_entity(reversed_transaction)

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, TransactionInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

    @staticmethod
    def metadata_for_reversal(
        transaction_id: models.TransactionId, reverse_reason: Optional[str] = None
    ) -> dict:
        if not reverse_reason:
            reverse_reason = "Voiding txn {transaction_id}".format(
                transaction_id=transaction_id
            )
        return {
            "reason": reverse_reason,
            "original_id": transaction_id,
            "is_reversal": True,
        }

    @staticmethod
    def idempotency_key_for_reversal(transaction_id) -> str:
        assert transaction_id, "transaction_id is provided"
        return "{prefix}-{transaction_id}".format(
            prefix=TRANSACTION_REVERSAL_PREFIX, transaction_id=transaction_id
        )
