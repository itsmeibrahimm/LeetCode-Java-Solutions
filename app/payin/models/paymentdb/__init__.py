import sqlalchemy

from app.payin.models.paymentdb.delete_payer_requests import DeletePayerRequestsTable
from app.payin.models.paymentdb.delete_payer_requests_metadata import (
    DeletePayerRequestsMetadataTable,
)
from app.payin.models.paymentdb.payer import PayerTable
from app.payin.models.paymentdb.pgp_customer import PgpCustomerTable
from app.payin.models.paymentdb.cart_payment import CartPaymentTable
from app.payin.models.paymentdb.payment_intent import PaymentIntentTable
from app.payin.models.paymentdb.payment_method import PaymentMethodTable
from app.payin.models.paymentdb.pgp_payment_intent import PgpPaymentIntentTable
from app.payin.models.paymentdb.pgp_payment_method import PgpPaymentMethodTable
from app.payin.models.paymentdb.payment_intent_adjustment_history import (
    PaymentIntentAdjustmentTable,
)
from app.payin.models.paymentdb.payment_charge import PaymentChargeTable
from app.payin.models.paymentdb.pgp_payment_charge import PgpPaymentChargeTable
from app.payin.models.paymentdb.refund import RefundTable
from app.payin.models.paymentdb.pgp_refund import PgpRefundTable

payin_paymentdb_metadata = sqlalchemy.MetaData()

payers = PayerTable(db_metadata=payin_paymentdb_metadata)
pgp_customers = PgpCustomerTable(db_metadata=payin_paymentdb_metadata)
cart_payments = CartPaymentTable(db_metadata=payin_paymentdb_metadata)
payment_intents = PaymentIntentTable(db_metadata=payin_paymentdb_metadata)
pgp_payment_intents = PgpPaymentIntentTable(db_metadata=payin_paymentdb_metadata)
payment_intents_adjustment_history = PaymentIntentAdjustmentTable(
    db_metadata=payin_paymentdb_metadata
)
payment_charges = PaymentChargeTable(db_metadata=payin_paymentdb_metadata)
pgp_payment_charges = PgpPaymentChargeTable(db_metadata=payin_paymentdb_metadata)
payment_methods = PaymentMethodTable(db_metadata=payin_paymentdb_metadata)
pgp_payment_methods = PgpPaymentMethodTable(db_metadata=payin_paymentdb_metadata)
refunds = RefundTable(db_metadata=payin_paymentdb_metadata)
pgp_refunds = PgpRefundTable(db_metadata=payin_paymentdb_metadata)
delete_payer_requests = DeletePayerRequestsTable(db_metadata=payin_paymentdb_metadata)
delete_payer_requests_metadata = DeletePayerRequestsMetadataTable(
    db_metadata=payin_paymentdb_metadata
)
