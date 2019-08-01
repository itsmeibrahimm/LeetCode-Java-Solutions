from gino import Gino

from app.ledger.models.paymentdb.mx_transaction import MxTransactionTable

ledger_paymentdb = Gino()
mx_transactions = MxTransactionTable(db_metadata=ledger_paymentdb)
