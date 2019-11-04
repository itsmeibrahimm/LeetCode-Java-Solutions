from app.payout.core.transaction.models import TransactionInternal
from app.payout.repository.bankdb.model.transaction import TransactionDBEntity


def get_transaction_internal_from_db_entity(transaction: TransactionDBEntity):
    fields = transaction.dict()

    # temp fix for currency lower-case vs upper-case issue
    # refactor once we finalize a convention
    # (Now, DB is upper case, but internal model is lower)
    currency = fields.get("currency")
    if currency:
        fields["currency"] = currency.lower()

    fields["payout_account_id"] = transaction.payment_account_id

    return TransactionInternal(**fields)
