import sqlalchemy

from app.payin.models.maindb.stripe_card import StripeCardTable
from app.payin.models.maindb.stripe_customer import StripeCustomerTable
from app.payin.models.maindb.stripe_dispute import StripeDisputeTable

payin_maindb_metadata = sqlalchemy.MetaData()

stripe_customers = StripeCustomerTable(db_metadata=payin_maindb_metadata)
stripe_cards = StripeCardTable(db_metadata=payin_maindb_metadata)
stripe_disputes = StripeDisputeTable(db_metadata=payin_maindb_metadata)
