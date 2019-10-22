from app.payout.repository.maindb.model.transfer import Transfer
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.types import TransferStatusType, TransferMethodType


async def determine_transfer_status_from_latest_submission(
    transfer: Transfer, stripe_transfer_repo: StripeTransferRepositoryInterface
):
    """
    Returns the transfer status corresponding to latest gateways specific status for this transfer id
    """

    if transfer.deleted_at:
        return TransferStatusType.DELETED

    if not transfer.method:
        return TransferStatusType.NEW

    if transfer.method == TransferMethodType.DOORDASH_PAY and transfer.submitted_at:
        return TransferStatusType.PAID

    if transfer.amount == 0 and transfer.submitted_at:
        return TransferStatusType.PAID

    if transfer.method == TransferMethodType.STRIPE:
        stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        if stripe_transfer:
            return stripe_status_to_transfer_status(stripe_transfer.stripe_status)
    else:
        if transfer.submitted_at:
            return TransferStatusType.PAID
    return TransferStatusType.NEW


def stripe_status_to_transfer_status(stripe_status):
    if stripe_status == "canceled":
        # NOTE: stripe used `canceled`, but we used `cancelled`
        return TransferStatusType.CANCELLED
    elif stripe_status == "paid":
        return TransferStatusType.PAID
    elif stripe_status == "pending":
        return TransferStatusType.PENDING
    elif stripe_status == "failed":
        return TransferStatusType.FAILED
    elif stripe_status == "in_transit":
        return TransferStatusType.IN_TRANSIT
    elif stripe_status == "created":
        return TransferStatusType.CREATED
    else:
        return None
