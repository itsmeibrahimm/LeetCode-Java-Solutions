import sqlalchemy

from app.payin.models.maindb.consumer_charge import ConsumerChargeTable
from app.payin.models.maindb.stripe_charge import StripeChargeTable
from app.payin.models.maindb.stripe_card import StripeCardTable
from app.payin.models.maindb.stripe_customer import StripeCustomerTable
from app.payin.models.maindb.stripe_dispute import StripeDisputeTable

payin_maindb_metadata = sqlalchemy.MetaData()

consumer_charges = ConsumerChargeTable(db_metadata=payin_maindb_metadata)
stripe_charges = StripeChargeTable(db_metadata=payin_maindb_metadata)
stripe_customers = StripeCustomerTable(db_metadata=payin_maindb_metadata)
stripe_cards = StripeCardTable(db_metadata=payin_maindb_metadata)
stripe_disputes = StripeDisputeTable(db_metadata=payin_maindb_metadata)
