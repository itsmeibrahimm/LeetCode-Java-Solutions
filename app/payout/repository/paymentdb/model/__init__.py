import sqlalchemy
from app.payout.repository.paymentdb.model.payout_lock import PayoutLockTable


payout_paymentdb_metadata = sqlalchemy.MetaData()
payout_lock = PayoutLockTable(db_metadata=payout_paymentdb_metadata)
