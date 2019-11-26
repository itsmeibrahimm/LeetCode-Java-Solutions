import pytz
from datetime import datetime, timedelta
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.jobs import retry_instant_payout
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository


async def retry_instant_payout_operation(payout_id: int, app_context: AppContext):
    """Script to retry instant payout.

    This is the function for on-call engineer to retry instant payout, which are typically in New status. The created
    time of the payout should be less than 15 hours, in order to leverage stripe idempotency key to avoid double pay.

    Usage:
        get into payment service admin pod, and type ipython
        >> from app.scripts.payout.instant_payout import retry_instant_payout_operation
        >> retry_instant_payout_operation(<payout_id>, app_context)

    :param payout_id: payout id
    :param app_context: app context
    :type payout_id: int
    :type app_context: AppContext
    :return: None, will print out operation log
    """

    payout_repo = PayoutRepository(app_context.payout_bankdb)

    log = app_context.log
    log.info("Start to retry instant payout")

    payout = await payout_repo.get_payout_by_id(payout_id=payout_id)
    if payout is None:
        log.warn("Fail to get payout record")
        return
    current_time = datetime.utcnow().replace(tzinfo=pytz.utc)
    if current_time - payout.created_at.replace(tzinfo=pytz.utc) > timedelta(hours=15):
        log.warn("Can not retry instant payout more than 15 hours")
        return

    payout_account_repo = PaymentAccountRepository(app_context.payout_maindb)
    payout_card_repo = PayoutCardRepository(app_context.payout_bankdb)
    stripe_managed_account_transfer_repo = StripeManagedAccountTransferRepository(
        app_context.payout_bankdb
    )
    stripe_payout_request_repo = StripePayoutRequestRepository(
        app_context.payout_bankdb
    )
    transaction_repo = TransactionRepository(app_context.payout_bankdb)
    req_context = build_req_context(app_context)
    stripe_async_client = req_context.stripe_async_client
    log = req_context.log

    await retry_instant_payout(
        payout=payout,
        payout_repo=payout_repo,
        payout_account_repo=payout_account_repo,
        payout_card_repo=payout_card_repo,
        stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
        stripe_payout_request_repo=stripe_payout_request_repo,
        transaction_repo=transaction_repo,
        stripe_async_client=stripe_async_client,
        log=log,
    )
