from datetime import datetime
from typing import List, Dict, Any

from doordash_lib.money import dollars_to_cents
from pydantic import ValidationError
from structlog import BoundLogger

from app.purchasecard.core.errors import (
    MarqetaTransactionNotFoundError,
    MarqetaTransactionEventNotFoundError,
    MarqetaAuthDataFormatInvalidError,
)
from app.purchasecard.core.transaction_event.models import (
    InternalMarqetaTransactionEvent,
    generate_internal_marqeta_transaction_event,
)
from app.purchasecard.core.utils import (
    enriched_error_parse_int,
    should_card_acceptor_be_examined,
)
from app.purchasecard.marqeta_external.marqeta_provider_client import (
    MarqetaProviderClient,
)
from app.purchasecard.marqeta_external.models import (
    MarqetaAuthData,
    MarqetaCardAcceptor,
)
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.repository.card_acceptor import CardAcceptorRepositoryInterface
from app.purchasecard.repository.marqeta_card_ownership import (
    MarqetaCardOwnershipRepositoryInterface,
)
from app.purchasecard.repository.marqeta_transaction import (
    MarqetaTransactionRepositoryInterface,
)
from app.purchasecard.repository.marqeta_transaction_event import (
    MarqetaTransactionEventRepositoryInterface,
)
import app.purchasecard.marqeta_external.errors as marqeta_error


class TransactionEventProcessor:
    def __init__(
        self,
        logger: BoundLogger,
        marqeta_client: MarqetaProviderClient,
        transaction_repo: MarqetaTransactionRepositoryInterface,
        transaction_event_repo: MarqetaTransactionEventRepositoryInterface,
        card_acceptor_repo: CardAcceptorRepositoryInterface,
        card_ownership_repo: MarqetaCardOwnershipRepositoryInterface,
    ):
        self.logger = logger
        self.transaction_repo = transaction_repo
        self.transaction_event_repo = transaction_event_repo
        self.card_acceptor_repo = card_acceptor_repo
        self.marqeta_client = marqeta_client
        self.card_ownership_repo = card_ownership_repo

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

    async def record_transaction_event(
        self, marqeta_user_token: str, anchor_day: datetime, shift_id: str
    ) -> List[InternalMarqetaTransactionEvent]:
        created_transaction_events = []
        auth_data_list = await self.get_auth_data_from_marqeta_client(
            marqeta_user_token=marqeta_user_token, anchor_day=anchor_day
        )
        for raw_auth_data in auth_data_list:
            try:
                auth_data = MarqetaAuthData(**raw_auth_data)
            except (AttributeError, TypeError, ValidationError):
                self.logger.warning(
                    "[record transaction event] get invalid format of auth data from Marqeta",
                    user_token=marqeta_user_token,
                    anchor_day=anchor_day.isoformat(),
                )
                raise MarqetaAuthDataFormatInvalidError()
            transaction_token = auth_data.token
            has_existing_transaction = await self.transaction_event_repo.get_transaction_event_by_token(
                transaction_token=transaction_token
            )
            if has_existing_transaction:
                continue

            # create new marqeta transaction event
            card_acceptor = await self.get_card_acceptor(auth_data)
            card_ownerships = await self.get_card_ownerships(auth_data)
            if card_ownerships:
                transaction_event = await self.transaction_event_repo.create_transaction_event(
                    token=transaction_token,
                    amount=dollars_to_cents(auth_data.amount),
                    metadata=raw_auth_data,
                    raw_type=auth_data.type,
                    ownership_id=card_ownerships[0].id,
                    shift_id=enriched_error_parse_int(shift_id, "shift_id"),
                    card_acceptor_id=card_acceptor.id if card_acceptor else None,
                )
                created_transaction_events.append(
                    generate_internal_marqeta_transaction_event(
                        transaction_event, card_acceptor
                    )
                )
        return created_transaction_events

    async def get_auth_data_from_marqeta_client(
        self, marqeta_user_token: str, anchor_day: datetime
    ) -> List[Dict[str, Any]]:
        try:
            return await self.marqeta_client.get_authorization_data(
                user_token=marqeta_user_token, anchor_day=anchor_day
            )
        except marqeta_error.MarqetaGetAuthDataInvalidResponseError:
            raise MarqetaAuthDataFormatInvalidError()

    async def get_card_acceptor(self, auth_data: MarqetaAuthData) -> CardAcceptor:
        card_acceptor_resp: MarqetaCardAcceptor = auth_data.card_acceptor
        return await self.card_acceptor_repo.get_or_create_card_acceptor(
            name=card_acceptor_resp.name,
            mid=card_acceptor_resp.mid,
            state=card_acceptor_resp.state,
            city=card_acceptor_resp.city,
            zip_code=card_acceptor_resp.zip,
            should_be_examined=should_card_acceptor_be_examined(
                card_acceptor_resp.name
            ),
        )

    async def get_card_ownerships(
        self, auth_data: MarqetaAuthData
    ) -> List[MarqetaCardOwnership]:
        return await self.card_ownership_repo.get_active_card_ownerships_by_card_id(
            card_id=auth_data.card_token
        )
