from app.purchasecard.core.errors import (
    MarqetaTransactionNotFoundError,
    MarqetaTransactionEventNotFoundError,
)
from app.purchasecard.core.transaction_event.models import (
    InternalMarqetaTransactionEvent,
    generate_internal_marqeta_transaction_event,
)
from app.purchasecard.core.utils import enriched_error_parse_int
from app.purchasecard.repository.card_acceptor import CardAcceptorRepositoryInterface
from app.purchasecard.repository.marqeta_transaction import (
    MarqetaTransactionRepositoryInterface,
)
from app.purchasecard.repository.marqeta_transaction_event import (
    MarqetaTransactionEventRepositoryInterface,
)


class TransactionEventProcessor:
    def __init__(
        self,
        transaction_repo: MarqetaTransactionRepositoryInterface,
        transaction_event_repo: MarqetaTransactionEventRepositoryInterface,
        card_acceptor_repo: CardAcceptorRepositoryInterface,
    ):
        self.transaction_repo = transaction_repo
        self.transaction_event_repo = transaction_event_repo
        self.card_acceptor_repo = card_acceptor_repo

    async def get_latest_marqeta_transaction_event(
        self, delivery_id: str
    ) -> InternalMarqetaTransactionEvent:
        int_delivery_id = enriched_error_parse_int(
            str_id=delivery_id, str_id_name="delivery id"
        )
        last_transaction = await self.transaction_repo.get_last_transaction_by_delivery_id(
            delivery_id=int_delivery_id
        )
        if last_transaction is None:
            raise MarqetaTransactionNotFoundError()
        transaction_event = await self.transaction_event_repo.get_transaction_event_by_token(
            transaction_token=last_transaction.token
        )
        if transaction_event is None:
            raise MarqetaTransactionEventNotFoundError()

        card_acceptor = (
            await self.card_acceptor_repo.get_card_acceptor_by_id(
                card_acceptor_id=transaction_event.card_acceptor_id
            )
            if transaction_event.card_acceptor_id
            else None
        )
        return generate_internal_marqeta_transaction_event(
            transaction_event, card_acceptor
        )
