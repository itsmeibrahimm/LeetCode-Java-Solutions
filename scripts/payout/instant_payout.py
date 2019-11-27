import pytz
from datetime import datetime, timedelta
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import build_req_context
from app.payout.core.instant_payout.models import InstantPayoutStatusType
from app.payout.jobs import retry_instant_payout
from app.payout.repository.bankdb.model.payout import PayoutUpdate
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestUpdate,
)
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

    ** Please make sure the payout created time is within 15 hours **

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


async def mark_payout_as_paid(payout_id: int, app_context: AppContext):
    """Script to mark payout as paid.

    This is the function for on-call engineer to mark a payout record and latest corresponding stripe payout request
    record as paid. Due to Webhook, stripe issue, and some other reasons, it may happen that payout records in payment
    database is in New or Pending status, while it's paid on stripe dashboard. So this script is to mark the status as
    paid.

    ** Please make sure the payout is actually paid in stripe **

    Usage:
        get into payment service admin pod, and type ipython
        >> from app.scripts.payout.instant_payout import mark_payout_as_paid
        >> mark_payout_as_paid(<payout_id>, app_context)

    :param payout_id: payout id
    :param app_context: app context
    :type payout_id: int
    :type app_context: AppContext
    :return: None, will print out operation log
    """
    payout_repo = PayoutRepository(app_context.payout_bankdb)
    stripe_payout_request_repo = StripePayoutRequestRepository(
        app_context.payout_bankdb
    )

    log = app_context.log

    data = PayoutUpdate(status=InstantPayoutStatusType.PAID)
    updated_payout = await payout_repo.update_payout_by_id(
        payout_id=payout_id, data=data
    )

    if updated_payout is None:
        log.warn("Can't find Payout record to update")
        return

    log.info("Updated payout {} to {}".format(payout_id, updated_payout.status))

    stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
        payout_id=payout_id
    )

    if stripe_payout_request is None:
        log.warn("Can't find corresponding StripePayoutRequest record to update")
        return

    data = StripePayoutRequestUpdate(status=InstantPayoutStatusType.PAID)
    updated_stripe_payout_request = await stripe_payout_request_repo.update_stripe_payout_request_by_id(
        stripe_payout_request_id=stripe_payout_request.id, data=data
    )

    if updated_stripe_payout_request is None:
        log.warn("Failed to Update StripePayoutRequest ")
        return

    log.info(
        "Updated StripePayoutRequest {} from {} to {}".format(
            stripe_payout_request.id,
            stripe_payout_request.status,
            updated_stripe_payout_request.status,
        )
    )


async def mark_payout_as_failed_and_detach_transactions(
    payout_id: int, app_context: AppContext
):
    """Script to mark payout as failed, and detach transactions.

    This script is used to detach transactions from payout record, and make the transactions available again. It will
    also mark payout and latest corresponding stripe payout request as failed.

    Usage:
        get into payment service admin pod, and type ipython
        >> from app.scripts.payout.instant_payout import mark_payout_as_failed_and_detach_transactions
        >> mark_payout_as_failed_and_detach_transactions(<payout_id>, app_context)

    :param payout_id: payout id
    :param app_context: app context
    :type payout_id: int
    :type app_context: AppContext
    :return: None, will print out operation log
    """
    payout_repo = PayoutRepository(app_context.payout_bankdb)
    stripe_payout_request_repo = StripePayoutRequestRepository(
        app_context.payout_bankdb
    )
    transaction_repo = TransactionRepository(app_context.payout_bankdb)

    log = app_context.log

    # Update payout status
    data = PayoutUpdate(status=InstantPayoutStatusType.FAILED)
    updated_payout = await payout_repo.update_payout_by_id(
        payout_id=payout_id, data=data
    )

    if updated_payout is None:
        log.warn("Can't find Payout record to update")
        return

    log.info("Updated payout {} to {}".format(payout_id, updated_payout.status))

    # Update stripe payout request status
    stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
        payout_id=payout_id
    )

    if stripe_payout_request is None:
        log.warn("Can't find corresponding StripePayoutRequest record to update")
    else:
        data = StripePayoutRequestUpdate(status=InstantPayoutStatusType.PAID)
        updated_stripe_payout_request = await stripe_payout_request_repo.update_stripe_payout_request_by_id(
            stripe_payout_request_id=stripe_payout_request.id, data=data
        )

        if updated_stripe_payout_request is None:
            log.warn("Failed to Update StripePayoutRequest ")
            return

    # Detach transactions, payout.transaction_ids not include fee_transaction id
    await transaction_repo.set_transaction_payout_id_by_ids(
        transaction_ids=updated_payout.transaction_ids, payout_id=None
    )

    log.info("Detached transactions for payout {}".format(payout_id))
