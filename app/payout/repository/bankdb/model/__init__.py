import sqlalchemy

from app.payout.repository.bankdb.model.payment_account_edit_history import (
    PaymentAccountEditHistoryTable,
)
from app.payout.repository.bankdb.model.payout import PayoutTable
from app.payout.repository.bankdb.model.payout_card import PayoutCardTable
from app.payout.repository.bankdb.model.payout_method import PayoutMethodTable
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestTable,
)
from app.payout.repository.bankdb.model.transaction import TransactionTable
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransferTable,
)


payout_bankdb_metadata = sqlalchemy.MetaData()
payout_card = PayoutCardTable(db_metadata=payout_bankdb_metadata)
payout_method = PayoutMethodTable(db_metadata=payout_bankdb_metadata)
payouts = PayoutTable(db_metadata=payout_bankdb_metadata)
stripe_payout_requests = StripePayoutRequestTable(db_metadata=payout_bankdb_metadata)
transactions = TransactionTable(db_metadata=payout_bankdb_metadata)
stripe_managed_account_transfers = StripeManagedAccountTransferTable(
    db_metadata=payout_bankdb_metadata
)
payment_account_edit_history = PaymentAccountEditHistoryTable(
    db_metadata=payout_bankdb_metadata
)
