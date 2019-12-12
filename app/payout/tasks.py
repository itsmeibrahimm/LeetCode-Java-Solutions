import json
import logging
from uuid import uuid4

from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.transfer.processors.create_transfer import (
    CreateTransferRequest,
    CreateTransfer,
)
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransferRequest,
    SubmitTransfer,
)
from app.payout.core.transfer.processors.weekly_create_transfer import (
    WeeklyCreateTransferRequest,
    WeeklyCreateTransfer,
)
from app.payout.models import PayoutTask
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository

log = logging.getLogger(__name__)


async def process_message(app_context: AppContext, message: str):
    transfer_repo = TransferRepository(database=app_context.payout_maindb)
    transaction_repo = TransactionRepository(database=app_context.payout_bankdb)
    payment_account_repo = PaymentAccountRepository(database=app_context.payout_maindb)
    payment_account_edit_history_repo = PaymentAccountEditHistoryRepository(
        database=app_context.payout_bankdb
    )
    stripe_transfer_repo = StripeTransferRepository(database=app_context.payout_maindb)
    managed_account_transfer_repo = ManagedAccountTransferRepository(
        database=app_context.payout_maindb
    )

    data = json.loads(message)
    if data["task_type"] == PayoutTask.WEEKLY_CREATE_TRANSFER.value:
        # convert to weekly create transfer
        weekly_create_transfer_req = WeeklyCreateTransferRequest(
            payout_day=data["fn_kwargs"]["payout_day"],
            payout_countries=data["fn_kwargs"]["payout_countries"],
            end_time=data["fn_kwargs"]["end_time"],
            unpaid_txn_start_time=data["fn_kwargs"]["unpaid_txn_start_time"],
            whitelist_payment_account_ids=data["fn_kwargs"][
                "whitelist_payment_account_ids"
            ],
            exclude_recently_updated_accounts=data["fn_kwargs"][
                "exclude_recently_updated_accounts"
            ],
        )
        req_context = build_req_context(
            app_context, task_name="WeeklyCreateTransferTask", task_id=str(uuid4())
        )
        weekly_create_transfer_op = WeeklyCreateTransfer(
            transfer_repo=transfer_repo,
            transaction_repo=transaction_repo,
            payment_account_repo=payment_account_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            stripe=req_context.stripe_async_client,
            payment_lock_manager=app_context.redis_lock_manager,
            logger=req_context.log,
            kafka_producer=app_context.kafka_producer,
            request=weekly_create_transfer_req,
        )
        await weekly_create_transfer_op.execute()
    elif data["task_type"] == PayoutTask.CREATE_TRANSFER.value:
        # convert to create transfer
        create_transfer_req = CreateTransferRequest(
            payout_account_id=data["fn_kwargs"]["payout_account_id"],
            transfer_type=data["fn_kwargs"]["transfer_type"],
            end_time=data["fn_kwargs"]["end_time"],
            start_time=data["fn_kwargs"]["start_time"],
            payout_countries=data["fn_kwargs"]["payout_countries"],
            created_by_id=data["fn_kwargs"]["created_by_id"],
            submit_after_creation=data["fn_kwargs"]["submit_after_creation"],
        )
        req_context = build_req_context(
            app_context, task_name="CreateTransferTask", task_id=str(uuid4())
        )
        create_transfer_op = CreateTransfer(
            transfer_repo=transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_repo=payment_account_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            transaction_repo=transaction_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            stripe=req_context.stripe_async_client,
            payment_lock_manager=app_context.redis_lock_manager,
            logger=req_context.log,
            kafka_producer=app_context.kafka_producer,
            request=create_transfer_req,
        )
        await create_transfer_op.execute()
    elif data["task_type"] == PayoutTask.SUBMIT_TRANSFER.value:
        # convert to submit transfer
        submit_transfer_req = SubmitTransferRequest(
            transfer_id=data["fn_kwargs"]["transfer_id"],
            method=data["fn_kwargs"]["method"],
            retry=data["fn_kwargs"]["retry"],
            submitted_by=data["fn_kwargs"]["submitted_by"],
        )
        req_context = build_req_context(
            app_context, task_name="SubmitTransferTask", task_id=str(uuid4())
        )
        submit_transfer_op = SubmitTransfer(
            transfer_repo=transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            transaction_repo=transaction_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            stripe=req_context.stripe_async_client,
            logger=req_context.log,
            request=submit_transfer_req,
        )
        await submit_transfer_op.execute()

    log.info(f"finished processing message: {message}")
    return True
