from gino import Gino

from app.payin.models.paymentdb.payer import PayerTable
from app.payin.models.paymentdb.pgp_customer import PgpCustomerTable
from app.payin.models.paymentdb.cart_payment import CartPaymentTable
from app.payin.models.paymentdb.payment_intent import PaymentIntentTable
from app.payin.models.paymentdb.pgp_payment_intent import PgpPaymentIntentTable

payin_paymentdb_metadata = Gino()

payers = PayerTable(db_metadata=payin_paymentdb_metadata)
pgp_customers = PgpCustomerTable(db_metadata=payin_paymentdb_metadata)
cart_payments = CartPaymentTable(db_metadata=payin_paymentdb_metadata)
payment_intents = PaymentIntentTable(db_metadata=payin_paymentdb_metadata)
pgp_payment_intents = PgpPaymentIntentTable(db_metadata=payin_paymentdb_metadata)
