from datetime import datetime

from pydantic import BaseModel
from structlog.stdlib import BoundLogger
from typing import Optional, Union, List

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.constants import DEFAULT_PAGE_SIZE
from app.payout.core.exceptions import transaction_bad_query_parameters
from app.payout.core.transaction.models import TransactionListInternal
from app.payout.core.transaction.utils import get_transaction_internal_from_db_entity
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
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.transaction_repo = transaction_repo

    async def _execute(self) -> TransactionListInternal:
        # validate the request
        self.validate_list_transactions_request(self.request)

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
        transaction_internal_list = []
        for transaction in transactions:
            transaction_internal_list.append(
                get_transaction_internal_from_db_entity(transaction)
            )
        return TransactionListInternal(
            data=transaction_internal_list,
            count=len(transaction_internal_list),
            new_offset=new_offset,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, TransactionListInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

    def validate_list_transactions_request(self, request: ListTransactionsRequest):
        # TODO: this should be moved to @root_validator at ListTransactionsRequest obj once we upgrade Pydantic to 1.0.0

        # the exclude fields will be allowed to restrict the query always
        raw_request = request.dict(
            skip_defaults=True, exclude={"offset", "limit", "unpaid", "time_range"}
        )
        raw_request_fields_set = {k: v for k, v in raw_request.items() if v is not None}
        raw_request_fields_name = set(raw_request_fields_set.keys())

        # case 1:
        # query by transaction ids only
        if {"transaction_ids"} == raw_request_fields_name:
            transaction_ids = raw_request.get("transaction_ids", [])
            # we do not allow size param yet, now, its always DEFAULT_PAGE_SIZE
            if len(transaction_ids) <= DEFAULT_PAGE_SIZE:
                return

        # case 2:
        # query by target_ids and target_type
        if {"target_ids", "target_type"} == raw_request_fields_name:
            return

        # case 3:
        # query by transfer_id OR payout_id
        if {"transfer_id"} == raw_request_fields_name or {
            "payout_id"
        } == raw_request_fields_name:
            return

        # case 4:
        # query by payment_account_id
        if {"payout_account_id"} == raw_request_fields_name:
            return

        self.logger.info(
            "[ListTransactions] request validation failed", extra=raw_request
        )

        raise transaction_bad_query_parameters(
            "Bad query parameters, supported query patterns: "
            f"  1. transaction ids (size<{DEFAULT_PAGE_SIZE})"
            "  2. target_ids and target_type"
            "  3. transfer_id or payout_id"
            "  4. payment_account_id"
        )
