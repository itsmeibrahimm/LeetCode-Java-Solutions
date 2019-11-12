from typing import Union

from structlog import BoundLogger

from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.payout.core.errors import (
    InstantPayoutBadRequestError,
    InstantPayoutErrorCode,
    instant_payout_error_message_maps,
)
from app.payout.core.instant_payout.models import (
    VerifyTransactionsRequest,
    VerifyTransactionsResponse,
    PAYABLE_TRANSACTION_STATES,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface


class VerifyTransactions(
    AsyncOperation[VerifyTransactionsRequest, VerifyTransactionsResponse]
):
    """Verify Transactions.
    """

    def __init__(
        self,
        request: VerifyTransactionsRequest,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.payout_account_id = request.payout_account_id
        self.amount = request.amount
        self.transaction_repo = transaction_repo

    async def _execute(self) -> VerifyTransactionsResponse:
        transactions = await self.transaction_repo.get_unpaid_transaction_by_payout_account_id_without_limit(
            payout_account_id=self.payout_account_id
        )
        # All transaction state must be payable
        if not all(
            transaction.state in PAYABLE_TRANSACTION_STATES
            for transaction in transactions
        ):
            self.logger.warn(
                "[Instant Payout Submit]: fail due to not all transactions are payable",
                request=self.request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.TRANSACTIONS_NOT_ALL_PAYABLE,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.TRANSACTIONS_NOT_ALL_PAYABLE
                ],
            )
        # All transactions' transfer_id must be None
        if not all(transaction.transfer_id is None for transaction in transactions):
            self.logger.warn(
                "[Instant Payout Submit]: fail due to not all transactions transfer id is null",
                request=self.request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.TRANSACTIONS_TRANSFER_ID_NOT_EMPTY,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.TRANSACTIONS_TRANSFER_ID_NOT_EMPTY
                ],
            )
        # All transactions' payout_id must be None
        if not all(transaction.payout_id is None for transaction in transactions):
            self.logger.warn(
                "[Instant Payout Submit]: fail due to not all transactions payout id is null",
                request=self.request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.TRANSACTIONS_PAYOUT_ID_NOT_EMPTY,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.TRANSACTIONS_PAYOUT_ID_NOT_EMPTY
                ],
            )
        # Sum of transaction must match amount
        if not sum([transaction.amount for transaction in transactions]) == self.amount:
            self.logger.warn(
                "[Instant Payout Submit]: fail due to transactions amount not match input amount",
                request=self.request.dict(),
            )
            raise InstantPayoutBadRequestError(
                error_code=InstantPayoutErrorCode.AMOUNT_BALANCE_MISMATCH,
                error_message=instant_payout_error_message_maps[
                    InstantPayoutErrorCode.AMOUNT_BALANCE_MISMATCH
                ],
            )

        transaction_ids = [transaction.id for transaction in transactions]
        return VerifyTransactionsResponse(transaction_ids=transaction_ids)

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, VerifyTransactionsResponse]:
        raise
