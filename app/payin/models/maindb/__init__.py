from gino import Gino

from app.payin.models.maindb.stripe_card import StripeCardTable
from app.payin.models.maindb.stripe_customer import StripeCustomerTable

payin_maindb_metadata = Gino()

stripe_customers = StripeCustomerTable(db_metadata=payin_maindb_metadata)
stripe_cards = StripeCardTable(db_metadata=payin_maindb_metadata)
