from datetime import datetime, timezone

import pytest
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND
from starlette.testclient import TestClient

from app.purchasecard.api.transaction_event.v0.models import TransactionEvent
from app.purchasecard.core.transaction_event.models import (
    InternalMarqetaTransactionEvent,
)
from app.purchasecard.core.transaction_event.processor import TransactionEventProcessor


class TestMarqetaTransactionEvent:
    @pytest.fixture
    def mock_processor(
        self,
        mock_marqeta_transaction_repo,
        mock_marqeta_transaction_event_repo,
        mock_card_acceptor_repo,
    ):
        return TransactionEventProcessor(
            transaction_repo=mock_marqeta_transaction_repo,
            transaction_event_repo=mock_marqeta_transaction_event_repo,
            card_acceptor_repo=mock_card_acceptor_repo,
        )

    def test_get_latest_marqeta_transaction_event(
        self, mock_processor: TransactionEventProcessor, client: TestClient
    ):
        response = client.get("/purchasecard/api/v0/marqeta/transaction_event/last/0")
        assert response.status_code == HTTP_404_NOT_FOUND

        response = client.get(
            "/purchasecard/api/v0/marqeta/transaction_event/last/delivery_id"
        )
        assert response.status_code == HTTP_400_BAD_REQUEST

        mock_transaction_event = InternalMarqetaTransactionEvent(
            created_at=datetime.now(timezone.utc),
            token="test_token",
            amount=100,
            transaction_type="purchase",
            shift_id=1234,
            card_acceptor_name="taco bell",
            card_inactive=False,
            insufficient_funds=False,
            is_unsuccessful_payment=False,
            raw_type="authorization",
            available_balance=0.0,
        )

        assert TransactionEvent(**mock_transaction_event.dict())
