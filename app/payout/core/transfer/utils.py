from app.payout.repository.maindb.model.transfer import Transfer, TransferStatus
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.models import TransferMethodType


async def determine_transfer_status_from_latest_submission(
    transfer: Transfer, stripe_transfer_repo: StripeTransferRepositoryInterface
):
    """
    Returns the transfer status corresponding to latest gateways specific status for this transfer id
    """

    if transfer.deleted_at:
        return TransferStatus.DELETED

    if not transfer.method:
        return TransferStatus.NEW

    if transfer.method == TransferMethodType.DOORDASH_PAY and transfer.submitted_at:
        return TransferStatus.PAID

    if transfer.amount == 0 and transfer.submitted_at:
        return TransferStatus.PAID

    if transfer.method == TransferMethodType.STRIPE:
        stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        if stripe_transfer:
            return TransferStatus.stripe_status_to_transfer_status(
                stripe_transfer.stripe_status
            )
    else:
        if transfer.submitted_at:
            return TransferStatus.PAID
    return TransferStatus.NEW
