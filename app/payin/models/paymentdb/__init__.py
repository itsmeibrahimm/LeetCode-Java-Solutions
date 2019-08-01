from gino import Gino

from app.payin.models.paymentdb.payer import PayerTable
from app.payin.models.paymentdb.pgp_customer import PgpCustomerTable

payin_paymentdb_metadata = Gino()

payers = PayerTable(db_metadata=payin_paymentdb_metadata)
pgp_customers = PgpCustomerTable(db_metadata=payin_paymentdb_metadata)
