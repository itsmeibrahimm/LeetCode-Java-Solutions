import sqlalchemy

from app.purchasecard.models.maindb.card_acceptor import CardAcceptorTable
from app.purchasecard.models.maindb.card_acceptor_store_association import (
    CardAcceptorStoreAssociationTable,
)
from app.purchasecard.models.maindb.delivery_funding import DeliveryFundingTable
from app.purchasecard.models.maindb.marqeta_card import MarqetaCardTable
from app.purchasecard.models.maindb.marqeta_card_ownership import (
    MarqetaCardOwnershipTable,
)
from app.purchasecard.models.maindb.marqeta_card_transition import (
    MarqetaCardTransitionTable,
)
from app.purchasecard.models.maindb.marqeta_decline_exemption import (
    MarqetaDeclineExemptionTable,
)
from app.purchasecard.models.maindb.marqeta_transaction import MarqetaTransactionTable
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEventTable,
)
from app.purchasecard.models.maindb.store_mastercard_data import (
    StoreMastercardDataTable,
)

purchasecard_maindb_metadata = sqlalchemy.MetaData()

card_acceptors = CardAcceptorTable(db_metadata=purchasecard_maindb_metadata)
card_acceptor_store_associations = CardAcceptorStoreAssociationTable(
    db_metadata=purchasecard_maindb_metadata
)
delivery_funding = DeliveryFundingTable(db_metadata=purchasecard_maindb_metadata)
marqeta_cards = MarqetaCardTable(db_metadata=purchasecard_maindb_metadata)
marqeta_card_ownerships = MarqetaCardOwnershipTable(
    db_metadata=purchasecard_maindb_metadata
)
marqeta_card_transitions = MarqetaCardTransitionTable(
    db_metadata=purchasecard_maindb_metadata
)
marqeta_decline_exemptions = MarqetaDeclineExemptionTable(
    db_metadata=purchasecard_maindb_metadata
)
marqeta_transactions = MarqetaTransactionTable(db_metadata=purchasecard_maindb_metadata)
marqeta_transaction_events = MarqetaTransactionEventTable(
    db_metadata=purchasecard_maindb_metadata
)
store_mastercard_data = StoreMastercardDataTable(
    db_metadata=purchasecard_maindb_metadata
)
