import uuid
from datetime import datetime
from typing import Optional

from pydantic import Json

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import ReqContext
from app.ledger.core.mx_transaction.utils import to_mx_ledger, to_mx_transaction
from app.ledger.repository.mx_transaction_repository import (
    InsertMxTransactionOutput,
    MxTransactionRepository,
)
from app.ledger.core.mx_transaction.model import MxTransaction, MxLedger
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxScheduledLedgerIntervalType,
    MxLedgerType,
    MxLedgerStateType,
)
from app.ledger.repository.mx_ledger_repository import (
    GetMxLedgerByAccountInput,
    InsertMxLedgerInput,
    GetMxLedgerByIdInput,
    UpdateMxLedgerSetInput,
    UpdateMxLedgerWhereInput,
    MxLedgerRepository,
)
from app.ledger.repository.mx_scheduled_ledger_repository import (
    GetMxScheduledLedgerInput,
    InsertMxScheduledLedgerInput,
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import InsertMxTransactionInput


async def create_mx_transaction_impl(
    app_context: AppContext,
    req_context: ReqContext,
    mx_transaction_repository: MxTransactionRepository,
    mx_ledger_repository: MxLedgerRepository,
    mx_scheduled_repository: MxScheduledLedgerRepository,
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

    # Step 1: Find or create an open mx_ledger
    mx_ledger = await get_or_create_mx_ledger(
        payment_account_id=payment_account_id,
        routing_key=routing_key,
        currency=currency,
        amount=amount,
        mx_ledger_repository=mx_ledger_repository,
        mx_scheduled_repository=mx_scheduled_repository,
        interval_type=interval_type,
        type=MxLedgerType.SCHEDULED,
    )

    # step 2: create mx_transaction object
    mx_transaction_to_insert = InsertMxTransactionInput(
        id=uuid.uuid4(),
        payment_account_id=payment_account_id,
        amount=amount,
        currency=currency,
        ledger_id=mx_ledger.id,
        idempotency_key=idempotency_key,
        routing_key=routing_key,
        target_type=target_type,
        target_id=target_id,
        legacy_transaction_id=legacy_transaction_id,
        context=context,
        metadata=metadata,
    )
    mx_transaction: InsertMxTransactionOutput = await mx_transaction_repository.insert_mx_transaction(
        mx_transaction_to_insert
    )

    # step 3: Update ledger's balance
    request_balance = UpdateMxLedgerSetInput(balance=amount)
    request_id = UpdateMxLedgerWhereInput(id=mx_ledger.id)
    await mx_ledger_repository.update_mx_ledger_balance(request_balance, request_id)

    return to_mx_transaction(mx_transaction)


# todo: add error handling
async def get_or_create_mx_ledger(
    type: MxLedgerType,
    payment_account_id: str,
    routing_key: datetime,
    currency: str,
    amount: int,
    mx_ledger_repository: MxLedgerRepository,
    mx_scheduled_repository: MxScheduledLedgerRepository,
    interval_type: MxScheduledLedgerIntervalType,
) -> MxLedger:

    # with given payment_account_id, routing_key and interval_type, retrieve open scheduled ledger
    get_scheduled_ledger_request = GetMxScheduledLedgerInput(
        payment_account_id=payment_account_id,
        routing_key=routing_key,
        interval_type=interval_type,
    )
    mx_scheduled_ledger = await mx_scheduled_repository.get_open_mx_scheduled_ledger_for_period(
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
            mx_ledger_id = uuid.uuid4()
            mx_ledger_to_insert = InsertMxLedgerInput(
                id=mx_ledger_id,
                type=type,
                currency=currency,
                state=MxLedgerStateType.OPEN.value,
                balance=amount,
                payment_account_id=payment_account_id,
                amount_paid=0,
            )
            created_mx_ledger = await mx_ledger_repository.insert_mx_ledger(
                mx_ledger_to_insert
            )

            mx_scheduled_ledger_id = uuid.uuid4()
            mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
                id=mx_scheduled_ledger_id,
                payment_account_id=payment_account_id,
                ledger_id=created_mx_ledger.id,
                interval_type=interval_type,
                start_time=mx_scheduled_repository.pacific_start_time_for_current_interval(
                    routing_key, interval_type
                ),
                end_time=mx_scheduled_repository.pacific_end_time_for_current_interval(
                    routing_key, interval_type
                ),
            )

            await mx_scheduled_repository.insert_mx_scheduled_ledger(
                mx_scheduled_ledger_to_insert
            )
            return to_mx_ledger(created_mx_ledger)
        return to_mx_ledger(mx_ledger)
    # if mx_scheduled_ledger found, retrieve the corresponding mx_ledger and return it
    mx_ledger_to_retrieve = GetMxLedgerByIdInput(id=mx_scheduled_ledger.ledger_id)
    mx_ledger_to_return = to_mx_ledger(
        await mx_ledger_repository.get_ledger_by_id(mx_ledger_to_retrieve)
    )
    return mx_ledger_to_return
