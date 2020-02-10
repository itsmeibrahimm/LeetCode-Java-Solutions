from datetime import datetime, timezone

from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_201_CREATED
from starlette.testclient import TestClient

from app.purchasecard.api.transaction_event.v0.models import TransactionEvent
from app.purchasecard.core.transaction_event.models import (
    InternalMarqetaTransactionEvent,
)


class TestMarqetaTransactionEvent:
    def test_get_latest_marqeta_transaction_event(self, client: TestClient):
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

    def test_record_transaction_event(self, client: TestClient):
        test_request = {
            "marqeta_user_token": "1",
            "anchor_day": "2020-01-29T19:06:21.639Z",
            "shift_id": 602829,
        }
        response = client.post(
            "/purchasecard/api/v0/marqeta/transaction_event", json=test_request
        )
        assert response.status_code == HTTP_201_CREATED
