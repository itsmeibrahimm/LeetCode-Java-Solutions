import sqlalchemy

from app.payout.repository.bankdb.model.payout import PayoutTable
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestTable,
)
from app.payout.repository.bankdb.model.transaction import TransactionTable
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransferTable,
)


payout_bankdb_metadata = sqlalchemy.MetaData()
payouts = PayoutTable(db_metadata=payout_bankdb_metadata)
stripe_payout_requests = StripePayoutRequestTable(db_metadata=payout_bankdb_metadata)
transactions = TransactionTable(db_metadata=payout_bankdb_metadata)
stripe_managed_account_transfers = StripeManagedAccountTransferTable(
    db_metadata=payout_bankdb_metadata
)
