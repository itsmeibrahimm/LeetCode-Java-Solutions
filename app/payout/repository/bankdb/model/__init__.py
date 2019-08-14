import sqlalchemy

from app.payout.repository.bankdb.model.payout import PayoutTable


payout_bankdb_metadata = sqlalchemy.MetaData()
payouts = PayoutTable(db_metadata=payout_bankdb_metadata)
