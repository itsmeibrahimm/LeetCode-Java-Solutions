from datetime import datetime

from pydantic import BaseModel
from structlog.stdlib import BoundLogger
from typing import Optional, Union, List

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.constants import DEFAULT_PAGE_SIZE
from app.payout.core.exceptions import transaction_bad_query_parameters
from app.payout.core.transaction.models import (
    TransactionListInternal,
    TransactionInternal,
)
from app.payout.repository.bankdb.model.transaction import TransactionDBEntity
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface
from app.payout import models


class TimeRange(BaseModel):
    start_time: Optional[datetime]
    end_time: Optional[datetime]


class ListTransactionsRequest(OperationRequest):
    transaction_ids: Optional[List[models.TransactionId]]
    target_ids: Optional[List[models.TransactionTargetId]]
    target_type: Optional[models.TransactionTargetType]
    transfer_id: Optional[models.TransferId]
    payout_id: Optional[models.PayoutId]
    payout_account_id: Optional[models.PayoutAccountId]
    time_range: Optional[TimeRange]
    unpaid: Optional[bool] = False
    offset: int = 0
    limit: int = DEFAULT_PAGE_SIZE


class ListTransactions(
    AsyncOperation[ListTransactionsRequest, TransactionListInternal]
):
    """
    Processor to list transactions based on different parameters
    """

    transaction_repo: TransactionRepositoryInterface

    def __init__(
        self,
        request: ListTransactionsRequest,
        *,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.transaction_repo = transaction_repo

    async def _execute(self) -> TransactionListInternal:
        # validate the request
        ListTransactions.validate_list_transactions_request(self.request)

        transactions: List[TransactionDBEntity] = []
        if self.request.transaction_ids:
            transactions = await self.transaction_repo.get_transaction_by_ids(
                transaction_ids=self.request.transaction_ids
            )
        elif self.request.target_ids and self.request.target_type:
            transactions = await self.transaction_repo.get_transaction_by_target_ids_and_type(
                target_ids=self.request.target_ids,
                target_type=self.request.target_type,
                offset=self.request.offset,
                limit=self.request.limit,
            )
        elif self.request.transfer_id:
            transactions = await self.transaction_repo.get_transaction_by_transfer_id(
                transfer_id=self.request.transfer_id,
                offset=self.request.offset,
                limit=self.request.limit,
            )
        elif self.request.payout_id:
            transactions = await self.transaction_repo.get_transaction_by_payout_id(
                payout_id=self.request.payout_id,
                offset=self.request.offset,
                limit=self.request.limit,
            )
        elif self.request.payout_account_id and self.request.unpaid:
            transactions = await self.transaction_repo.get_unpaid_transaction_by_payout_account_id(
                payout_account_id=self.request.payout_account_id,
                start_time=self.request.time_range.start_time
                if self.request.time_range
                else None,
                end_time=self.request.time_range.end_time
                if self.request.time_range
                else None,
                offset=self.request.offset,
                limit=self.request.limit,
            )
        elif self.request.payout_account_id:
            transactions = await self.transaction_repo.get_transaction_by_payout_account_id(
                payout_account_id=self.request.payout_account_id,
                start_time=self.request.time_range.start_time
                if self.request.time_range
                else None,
                end_time=self.request.time_range.end_time
                if self.request.time_range
                else None,
                offset=self.request.offset,
                limit=self.request.limit,
            )
        new_offset: Optional[int] = None
        if self.request.offset is not None:
            new_offset = self.request.offset + len(transactions)
        transaction_internal_list = [
            TransactionInternal(
                **transaction.dict(), payout_account_id=transaction.payment_account_id
            )
            for transaction in transactions
        ]
        return TransactionListInternal(
            data=transaction_internal_list,
            count=len(transaction_internal_list),
            new_offset=new_offset,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, TransactionListInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

    @staticmethod
    def validate_list_transactions_request(request: ListTransactionsRequest):
        # maximum length of transaction_ids we support is DEFAULT_PAGE_SIZE
        if request.transaction_ids and len(request.transaction_ids) > DEFAULT_PAGE_SIZE:
            raise transaction_bad_query_parameters(
                "The length of transaction_ids is too long, please send a shorter list (<= 100)."
            )
        # support only transfer_id or payout_id
        if request.transfer_id and request.payout_id:
            raise transaction_bad_query_parameters(
                "You can only fetch transactions by transfer_id or payout_id, "
                "filtering by both transfer_id and payout_id is not supported."
            )
        # no query parameter is provided; time_range is not supported alone
        if (
            not request.transaction_ids
            and not request.target_ids
            and not request.target_type
            and not request.transfer_id
            and not request.payout_id
            and not request.payout_account_id
            and not request.time_range
        ):
            raise transaction_bad_query_parameters(
                "Your search range is too broad, please pass in at least one query "
                "parameter to fetch a list of transactions."
            )
        # target_type has to be provided as well if target_id_list is provided
        if request.target_ids and not request.target_type:
            raise transaction_bad_query_parameters(
                "Missed required parameter for target_type if fetching by "
                "target_id_list {}".format(request.target_ids)
            )
        # target_type is not supported alone
        if request.target_type and not request.target_ids:
            raise transaction_bad_query_parameters(
                "Fetching a list of transactions by target_type is not supported, "
                "please pass in a list of target_id for this type of retrieval."
            )
