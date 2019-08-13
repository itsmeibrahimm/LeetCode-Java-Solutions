import sqlalchemy

from app.ledger.models.paymentdb.mx_ledger import MxLedgerTable
from app.ledger.models.paymentdb.mx_scheduled_ledger import MxScheduledLedgerTable
from app.ledger.models.paymentdb.mx_transaction import MxTransactionTable

ledger_paymentdb = sqlalchemy.MetaData()

mx_transactions = MxTransactionTable(db_metadata=ledger_paymentdb)
mx_ledgers = MxLedgerTable(db_metadata=ledger_paymentdb)
mx_scheduled_ledgers = MxScheduledLedgerTable(db_metadata=ledger_paymentdb)
