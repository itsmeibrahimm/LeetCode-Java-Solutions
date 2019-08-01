from gino import Gino

from app.payout.repository.maindb.model.payment_account import PaymentAccountTable
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountTable,
)

payout_maindb_metadata = Gino()

payment_accounts = PaymentAccountTable(db_metadata=payout_maindb_metadata)
stripe_managed_accounts = StripeManagedAccountTable(db_metadata=payout_maindb_metadata)
