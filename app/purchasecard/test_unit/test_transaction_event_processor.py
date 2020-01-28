import json
from datetime import datetime, timezone

import pytest
from asynctest import CoroutineMock, MagicMock

from app.purchasecard.core.errors import (
    MarqetaTransactionNotFoundError,
    MarqetaTransactionEventNotFoundError,
)
from app.purchasecard.core.transaction_event.models import (
    InternalMarqetaTransactionEvent,
)
from app.purchasecard.core.transaction_event.processor import TransactionEventProcessor
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEvent,
)
from app.testcase_utils import validate_expected_items_in_dict


@pytest.mark.asyncio
class TestTransactionEventProcessor:
    @pytest.fixture(autouse=True)
    def setup(
        self,
        mock_marqeta_transaction_event_repo,
        mock_marqeta_transaction_repo,
        mock_card_acceptor_repo,
    ):
        timestamp = datetime.now(timezone.utc)
        self.processor = TransactionEventProcessor(
            transaction_event_repo=mock_marqeta_transaction_event_repo,
            transaction_repo=mock_marqeta_transaction_repo,
            card_acceptor_repo=mock_card_acceptor_repo,
        )
        self.mock_card_acceptor = CardAcceptor(
            id=123,
            created_at=timestamp,
            mid="mid",
            name="card_acceptor_name",
            city="city",
            zip_code="123",
            state="state",
            is_blacklisted=False,
            blacklisted_by_id=False,
            should_be_examined=False,
        )
        self.mock_transaction_event = MarqetaTransactionEvent(
            id=123,
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            metadata=json.dumps(
                {
                    "response": {},
                    "type": "authorization",
                    "gpa": {"available_balance": 10.0},
                }
            ),
            ownership_id=123,
            shift_id=123,
            raw_type="authorization",
            card_acceptor_id=123,
        )
        self.mock_transaction_event2 = MarqetaTransactionEvent(
            id=123,
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            metadata=json.dumps(
                {
                    "response": {"code": "1016"},
                    "type": "authorization",
                    "gpa": {"available_balance": 10.0},
                }
            ),
            ownership_id=123,
            shift_id=123,
            raw_type="authorization",
            card_acceptor_id=123,
        )
        self.mock_transaction_event3 = MarqetaTransactionEvent(
            id=123,
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            metadata=json.dumps(
                {
                    "response": {"code": "0014"},
                    "type": "authorization",
                    "gpa": {"available_balance": 10.0},
                }
            ),
            ownership_id=123,
            shift_id=123,
            raw_type="authorization",
            card_acceptor_id=123,
        )
        self.expected_result = InternalMarqetaTransactionEvent(
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            shift_id=123,
            card_acceptor_name="card_acceptor_name",
            card_inactive=False,
            insufficient_funds=False,
            is_unsuccessful_payment=False,
            raw_type="authorization",
            available_balance=10.0,
        )
        self.expected_result2 = InternalMarqetaTransactionEvent(
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            shift_id=123,
            card_acceptor_name=None,
            card_inactive=False,
            insufficient_funds=False,
            is_unsuccessful_payment=False,
            raw_type="authorization",
            available_balance=10.0,
        )
        self.expected_result3 = InternalMarqetaTransactionEvent(
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            shift_id=123,
            card_acceptor_name=None,
            card_inactive=False,
            insufficient_funds=True,
            is_unsuccessful_payment=True,
            raw_type="authorization",
            available_balance=10.0,
        )
        self.expected_result4 = InternalMarqetaTransactionEvent(
            created_at=timestamp,
            token="test_token",
            amount=123,
            transaction_type="purchase",
            shift_id=123,
            card_acceptor_name=None,
            card_inactive=True,
            insufficient_funds=False,
            is_unsuccessful_payment=False,
            raw_type="authorization",
            available_balance=10.0,
        )

    async def test_get_latest_marqeta_transaction_event_exception(self):
        self.processor.transaction_repo.get_last_transaction_by_delivery_id = CoroutineMock(
            return_value=None
        )
        with pytest.raises(MarqetaTransactionNotFoundError):
            await self.processor.get_latest_marqeta_transaction_event("123")

        self.processor.transaction_repo.get_last_transaction_by_delivery_id = CoroutineMock(
            return_value=MagicMock()
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=None
        )
        with pytest.raises(MarqetaTransactionEventNotFoundError):
            await self.processor.get_latest_marqeta_transaction_event("123")

    async def test_get_latest_marqeta_transaction_event_with_card_acceptor(self):
        self.processor.transaction_repo.get_last_transaction_by_delivery_id = CoroutineMock(
            return_value=MagicMock()
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=self.mock_transaction_event
        )
        self.processor.card_acceptor_repo.get_card_acceptor_by_id = CoroutineMock(
            return_value=self.mock_card_acceptor
        )
        transaction_event = await self.processor.get_latest_marqeta_transaction_event(
            "123"
        )
        validate_expected_items_in_dict(
            expected=self.expected_result.dict(), actual=transaction_event.dict()
        )

    async def test_get_latest_marqeta_transaction_event_without_card_acceptor(self):
        self.processor.transaction_repo.get_last_transaction_by_delivery_id = CoroutineMock(
            return_value=MagicMock(token="test_token")
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=self.mock_transaction_event
        )
        self.processor.card_acceptor_repo.get_card_acceptor_by_id = CoroutineMock(
            return_value=None
        )
        transaction_event = await self.processor.get_latest_marqeta_transaction_event(
            "123"
        )
        validate_expected_items_in_dict(
            expected=self.expected_result2.dict(), actual=transaction_event.dict()
        )

    async def test_get_latest_marqeta_transaction_event_unsuccessful_payment(self):
        self.processor.transaction_repo.get_last_transaction_by_delivery_id = CoroutineMock(
            return_value=MagicMock(token="test_token")
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=self.mock_transaction_event2
        )
        self.processor.card_acceptor_repo.get_card_acceptor_by_id = CoroutineMock(
            return_value=None
        )
        transaction_event = await self.processor.get_latest_marqeta_transaction_event(
            "123"
        )
        validate_expected_items_in_dict(
            expected=self.expected_result3.dict(), actual=transaction_event.dict()
        )

    async def test_get_latest_marqeta_transaction_event_inactive_card(self):
        self.processor.transaction_repo.get_last_transaction_by_delivery_id = CoroutineMock(
            return_value=MagicMock(token="test_token")
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=self.mock_transaction_event3
        )
        self.processor.card_acceptor_repo.get_card_acceptor_by_id = CoroutineMock(
            return_value=None
        )
        transaction_event = await self.processor.get_latest_marqeta_transaction_event(
            "123"
        )
        validate_expected_items_in_dict(
            expected=self.expected_result4.dict(), actual=transaction_event.dict()
        )
