import sqlalchemy

from app.purchasecard.models.paymentdb.auth_request import AuthRequestTable
from app.purchasecard.models.paymentdb.auth_request_state import AuthRequestStateTable

purchasecard_paymentdb_metadata = sqlalchemy.MetaData()

auth_request = AuthRequestTable(db_metadata=purchasecard_paymentdb_metadata)
auth_request_state = AuthRequestStateTable(db_metadata=purchasecard_paymentdb_metadata)
