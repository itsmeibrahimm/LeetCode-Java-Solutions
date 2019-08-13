from datetime import datetime
from typing import Optional

from pydantic import Json

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext
from app.ledger.core.mx_transaction.utils import to_mx_transaction
from app.ledger.repository.mx_transaction_repository import (
    MxTransactionRepository,
    InsertMxTransactionWithLedgerInput,
)
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxScheduledLedgerIntervalType,
    MxLedgerType,
)
from app.ledger.repository.mx_ledger_repository import (
    GetMxLedgerByAccountInput,
    MxLedgerRepository,
)
from app.ledger.repository.mx_scheduled_ledger_repository import (
    GetMxScheduledLedgerInput,
    MxScheduledLedgerRepository,
)


async def create_mx_transaction_impl(
    app_context: AppContext,
    req_context: ReqContext,
    mx_transaction_repository: MxTransactionRepository,
    mx_ledger_repository: MxLedgerRepository,
    mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    payment_account_id: str,
    target_type: MxTransactionType,
    amount: int,
    currency: str,
    idempotency_key: str,
    routing_key: datetime,
    interval_type: MxScheduledLedgerIntervalType,
    target_id: Optional[str] = None,
    context: Optional[Json] = None,
    metadata: Optional[Json] = None,
    legacy_transaction_id: Optional[str] = None,
) -> MxTransaction:
    req_context.log.info(
        "[create_mx_transaction_impl] payment_account_id:%s, target_type:%s",
        payment_account_id,
        target_type.value,
    )

    # get or create mx_ledger and mx_scheduled_ledger and create mx_txn attached and update corresponding balance
    mx_transaction = await create_mx_txn_and_create_or_update_ledger(
        type=MxLedgerType.SCHEDULED,
        payment_account_id=payment_account_id,
        routing_key=routing_key,
        currency=currency,
        amount=amount,
        idempotency_key=idempotency_key,
        target_type=target_type,
        target_id=target_id,
        mx_transaction_repository=mx_transaction_repository,
        mx_ledger_repository=mx_ledger_repository,
        mx_scheduled_ledger_repository=mx_scheduled_ledger_repository,
        interval_type=interval_type,
        legacy_transaction_id=legacy_transaction_id,
        context=context,
        metadata=metadata,
    )
    return mx_transaction


# todo: add error handling
async def create_mx_txn_and_create_or_update_ledger(
    type: MxLedgerType,
    payment_account_id: str,
    routing_key: datetime,
    currency: str,
    amount: int,
    mx_transaction_repository: MxTransactionRepository,
    mx_ledger_repository: MxLedgerRepository,
    mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    idempotency_key: str,
    target_type: MxTransactionType,
    interval_type: MxScheduledLedgerIntervalType,
    legacy_transaction_id: Optional[str] = None,
    target_id: Optional[str] = None,
    context: Optional[Json] = None,
    metadata: Optional[Json] = None,
) -> MxTransaction:

    # with given payment_account_id, routing_key and interval_type, retrieve open scheduled ledger
    get_scheduled_ledger_request = GetMxScheduledLedgerInput(
        payment_account_id=payment_account_id,
        routing_key=routing_key,
        interval_type=interval_type,
    )
    mx_scheduled_ledger = await mx_scheduled_ledger_repository.get_open_mx_scheduled_ledger_for_period(
        get_scheduled_ledger_request
    )
    # if not found, retrieve open ledger for current payment_account
    if not mx_scheduled_ledger:
        get_mx_ledger_request = GetMxLedgerByAccountInput(
            payment_account_id=payment_account_id
        )
        mx_ledger = await mx_ledger_repository.get_open_ledger_for_payment_account(
            get_mx_ledger_request
        )
        # if not found, create new mx_scheduled_ledger and mx_ledger
        if not mx_ledger:
            # construct input and insert
            request_input = InsertMxTransactionWithLedgerInput(
                currency=currency,
                amount=amount,
                type=type,
                payment_account_id=payment_account_id,
                interval_type=interval_type,
                routing_key=routing_key,
                idempotency_key=idempotency_key,
                target_type=target_type,
                legacy_transaction_id=legacy_transaction_id,
                target_id=target_id,
                context=context,
                metadata=metadata,
            )

            created_mx_txn = await mx_transaction_repository.create_ledger_and_insert_mx_transaction(
                request_input, mx_scheduled_ledger_repository
            )
            return to_mx_transaction(created_mx_txn)
        # found open ledger, create transaction attach to it and update balance
        request_input = InsertMxTransactionWithLedgerInput(
            currency=currency,
            amount=amount,
            type=type,
            payment_account_id=payment_account_id,
            interval_type=interval_type,
            routing_key=routing_key,
            idempotency_key=idempotency_key,
            target_type=target_type,
            legacy_transaction_id=legacy_transaction_id,
            target_id=target_id,
            context=context,
            metadata=metadata,
        )
        created_mx_txn = await mx_transaction_repository.insert_mx_transaction_and_update_ledger(
            request_input, mx_ledger_repository, mx_ledger.id
        )
        return to_mx_transaction(created_mx_txn)

    # if mx_scheduled_ledger found, retrieve the corresponding mx_ledger, create transaction attached and update balance
    request_input = InsertMxTransactionWithLedgerInput(
        id=mx_scheduled_ledger.ledger_id,
        currency=currency,
        amount=amount,
        type=type,
        payment_account_id=payment_account_id,
        interval_type=interval_type,
        routing_key=routing_key,
        idempotency_key=idempotency_key,
        target_type=target_type,
        target_id=target_id,
        context=context,
        metadata=metadata,
    )
    created_mx_txn = await mx_transaction_repository.insert_mx_transaction_and_update_ledger(
        request_input, mx_ledger_repository, mx_scheduled_ledger.ledger_id
    )
    return to_mx_transaction(created_mx_txn)
