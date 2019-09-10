import sqlalchemy

from app.payout.repository.maindb.model.managed_account_transfer import (
    ManagedAccountTransferTable,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccountTable
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountTable,
)
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferTable
from app.payout.repository.maindb.model.transfer import TransferTable

payout_maindb_metadata = sqlalchemy.MetaData()

payment_accounts = PaymentAccountTable(db_metadata=payout_maindb_metadata)
stripe_managed_accounts = StripeManagedAccountTable(db_metadata=payout_maindb_metadata)
stripe_transfers = StripeTransferTable(db_metadata=payout_maindb_metadata)
transfers = TransferTable(db_metadata=payout_maindb_metadata)
managed_account_transfers = ManagedAccountTransferTable(
    db_metadata=payout_maindb_metadata
)
