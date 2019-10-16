from app.payout.core.transaction.types import TransactionInternal
from app.payout.repository.bankdb.model.transaction import TransactionDBEntity


def to_transaction_internal(transaction: TransactionDBEntity):
    return TransactionInternal(
        **transaction.dict(), payout_account_id=transaction.payment_account_id
    )
