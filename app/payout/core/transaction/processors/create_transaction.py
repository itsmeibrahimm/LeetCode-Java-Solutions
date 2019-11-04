from datetime import datetime

from structlog.stdlib import BoundLogger
from typing import Optional, Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.transaction.models import TransactionInternal
from app.payout.core.transaction.utils import get_transaction_internal_from_db_entity
from app.payout.repository.bankdb.model.transaction import TransactionCreateDBEntity
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface


class CreateTransactionRequest(OperationRequest):
    amount: int
    amount_paid: Optional[
        int
    ] = None  # will be default to 0 at DB layer, same default behavior as DSJ
    payment_account_id: int
    idempotency_key: str
    currency: str
    target_id: int
    target_type: str
    transfer_id: Optional[int]
    created_at: Optional[datetime]
    created_by_id: Optional[int]
    notes: Optional[str]
    metadata: Optional[str]
    state: Optional[str]
    updated_at: Optional[datetime]
    dsj_id: Optional[int]
    payout_id: Optional[int]
    inserted_at: Optional[datetime]


class CreateTransaction(AsyncOperation[CreateTransactionRequest, TransactionInternal]):
    """
    Processor to create a transaction based on different parameters
    """

    transaction_repo: TransactionRepositoryInterface

    def __init__(
        self,
        request: CreateTransactionRequest,
        *,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.transaction_repo = transaction_repo

    async def _execute(self) -> TransactionInternal:
        db_entity_request = self._convert_request_to_db_entity_request()
        transaction = await self.transaction_repo.create_transaction(
            data=db_entity_request
        )

        return get_transaction_internal_from_db_entity(transaction)

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, TransactionInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

    def _convert_request_to_db_entity_request(self):
        """
        helper function to convert processor level request to db/repo level request
        handle default values as needed

        :return:
        """
        fields = self.request.dict()
        if fields.get("amount_paid") is None:
            fields["amount_paid"] = 0  # default to 0 as in DSJ

        # temp fix for currency lower-case vs upper-case issue
        # refactor once we finalize a convention
        # (Now, DB is upper case, but internal model is lower)
        currency = fields.get("currency")
        if currency:
            fields["currency"] = currency.upper()

        return TransactionCreateDBEntity(**fields)
