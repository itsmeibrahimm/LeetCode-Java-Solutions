import json
from datetime import datetime, timezone

import pytest
from asynctest import CoroutineMock, MagicMock

from app.purchasecard.core.errors import (
    MarqetaTransactionNotFoundError,
    MarqetaTransactionEventNotFoundError,
    MarqetaAuthDataFormatInvalidError,
)
from app.purchasecard.core.transaction_event.models import (
    InternalMarqetaTransactionEvent,
)
from app.purchasecard.core.transaction_event.processor import TransactionEventProcessor
from app.purchasecard.marqeta_external.models import MarqetaCardAcceptor
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEvent,
)
from app.testcase_utils import validate_expected_items_in_dict
import app.purchasecard.marqeta_external.errors as marqeta_error


@pytest.mark.asyncio
class TestTransactionEventProcessor:
    @pytest.fixture
    def mock_marqeta_auth_data(self):
        return [
            {
                "acquirer": {
                    "institution_id_code": "003684",
                    "retrieval_reference_number": "000720315465",
                    "system_trace_audit_number": "315465",
                },
                "acquirer_fee_amount": 0,
                "acting_user_token": "4162250",
                "amount": 11.55,
                "approval_code": "751598",
                "card": {"last_four": "6392", "metadata": {}},
                "card_acceptor": {
                    "city": "DELAWARE",
                    "country": "USA",
                    "mcc": "5814",
                    "mcc_groups": ["b4b7cc10-1a3b-11e5-9fa3-005056aa121d"],
                    "mid": "4445197794149",
                    "name": "WENDY'S #0012",
                    "network_mid": "4445197794149",
                    "poi": {
                        "card_presence": "1",
                        "cardholder_presence": "1",
                        "channel": "OTHER",
                        "partial_approval_capable": "1",
                        "pin_present": "false",
                        "processing_type": "MAGSTRIPE",
                        "tid": "94149015",
                    },
                    "state": "OH",
                    "zip": "43015",
                },
                "card_security_code_verification": {
                    "response": {"code": "0000", "memo": "Card security code match"},
                    "type": "CVV1",
                },
                "card_token": "card-2931885",
                "created_time": "2020-01-07T23:14:57Z",
                "currency_code": "USD",
                "currency_conversion": {
                    "network": {
                        "conversion_rate": 1.0,
                        "original_amount": 11.55,
                        "original_currency_code": "840",
                    }
                },
                "duration": 571,
                "gpa": {
                    "available_balance": 0.0,
                    "balances": {
                        "USD": {
                            "available_balance": 0.0,
                            "credit_balance": 0.0,
                            "currency_code": "USD",
                            "impacted_amount": -11.55,
                            "ledger_balance": 30.06,
                            "pending_credits": 0.0,
                        }
                    },
                    "credit_balance": 0.0,
                    "currency_code": "USD",
                    "impacted_amount": -11.55,
                    "ledger_balance": 30.06,
                    "pending_credits": 0.0,
                },
                "gpa_order": {
                    "amount": 11.55,
                    "created_time": "2020-01-07T23:14:58Z",
                    "currency_code": "USD",
                    "funding": {
                        "amount": 11.55,
                        "gateway_log": {
                            "duration": 306,
                            "message": "Approved or completed successfully",
                            "order_number": "5bdf7eb7-e175-4474-8aca-a187f63e5394",
                            "response": {
                                "code": "200",
                                "data": {
                                    "jit_funding": {
                                        "acting_user_token": "4162250",
                                        "amount": 11.55,
                                        "method": "pgfs.authorization",
                                        "token": "b722ab9e-8bd6-4ac9-901a-d09880eb741d",
                                        "user_token": "4162250",
                                    }
                                },
                            },
                            "timed_out": False,
                            "transaction_id": "b722ab9e-8bd6-4ac9-901a-d09880eb741d",
                        },
                        "source": {
                            "active": True,
                            "created_time": "2016-01-22T21:16:05Z",
                            "is_default_account": False,
                            "last_modified_time": "2016-01-22T21:16:05Z",
                            "name": "DoorDash Program Gateway Funding Source",
                            "token": "**********d07e",
                            "type": "programgateway",
                        },
                    },
                    "funding_source_token": "**********d07e",
                    "jit_funding": {
                        "acting_user_token": "4162250",
                        "amount": 11.55,
                        "method": "pgfs.authorization",
                        "token": "b722ab9e-8bd6-4ac9-901a-d09880eb741d",
                        "user_token": "4162250",
                    },
                    "last_modified_time": "2020-01-07T23:14:58Z",
                    "response": {
                        "code": "0000",
                        "memo": "Approved or completed successfully",
                    },
                    "state": "PENDING",
                    "token": "40c4b9b6-4260-43d3-9416-211d03bf822f",
                    "transaction_token": "91e52a0b-34e3-4c95-a883-b089d5413d7a",
                    "user_token": "4162250",
                },
                "identifier": "381947223",
                "is_recurring": False,
                "issuer_payment_node": "2bcf2014292e623696cc2a8cb4089e06",
                "issuer_received_time": "2020-01-07T23:14:57.862Z",
                "network": "MASTERCARD",
                "request_amount": 11.55,
                "response": {
                    "code": "0000",
                    "memo": "Approved or completed successfully",
                },
                "settlement_date": "2020-01-07T00:00:00Z",
                "state": "PENDING",
                "token": "5bdf7eb7-e175-4474-8aca-a187f63e5394",
                "type": "authorization",
                "user": {"metadata": {}},
                "user_token": "4162250",
                "user_transaction_time": "2020-01-07T23:14:57Z",
            }
        ]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mock_marqeta_transaction_event_repo,
        mock_marqeta_transaction_repo,
        mock_card_acceptor_repo,
        mock_marqeta_card_ownership_repo,
    ):
        timestamp = datetime.now(timezone.utc)
        self.processor = TransactionEventProcessor(
            logger=MagicMock(),
            marqeta_client=MagicMock(),
            transaction_event_repo=mock_marqeta_transaction_event_repo,
            transaction_repo=mock_marqeta_transaction_repo,
            card_acceptor_repo=mock_card_acceptor_repo,
            card_ownership_repo=mock_marqeta_card_ownership_repo,
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

    async def test_get_auth_data_from_marqeta_client(self):
        test_result = [{"test": "test"}]
        self.processor.marqeta_client.get_authorization_data = CoroutineMock()
        self.processor.marqeta_client.get_authorization_data.return_value = test_result
        test = await self.processor.get_auth_data_from_marqeta_client(
            marqeta_user_token="token", anchor_day=datetime.utcnow()
        )
        assert test == test_result

        self.processor.marqeta_client.get_authorization_data.side_effect = (
            marqeta_error.MarqetaGetAuthDataInvalidResponseError
        )
        with pytest.raises(MarqetaAuthDataFormatInvalidError):
            await self.processor.get_auth_data_from_marqeta_client(
                marqeta_user_token="token", anchor_day=datetime.utcnow()
            )

    async def test_get_card_acceptor(self):
        mock_card_acceptor = MarqetaCardAcceptor(
            mid="test_mid",
            name="test_parking_lot",
            state="test_state",
            zip="test_zipcode",
            city="test_city",
        )
        mock_auth_data = MagicMock(card_acceptor=mock_card_acceptor)
        self.processor.card_acceptor_repo.get_or_create_card_acceptor = CoroutineMock(
            return_value=MagicMock()
        )
        result = await self.processor.get_card_acceptor(auth_data=mock_auth_data)
        assert result

    async def test_get_card_ownership(self):
        mock_auth_data = MagicMock(card_token="test_token")
        self.processor.card_ownership_repo.get_active_card_ownerships_by_card_id = CoroutineMock(
            return_value=MagicMock()
        )
        result = await self.processor.get_card_ownerships(auth_data=mock_auth_data)
        assert result

    async def test_record_transaction_event_empty_auth(self):
        self.processor.get_auth_data_from_marqeta_client = CoroutineMock(
            return_value=[]
        )
        result = await self.processor.record_transaction_event(
            marqeta_user_token="test_token",
            anchor_day=datetime.utcnow(),
            shift_id="123",
        )
        assert result == []

    async def test_record_transaction_event_invalid_auth_format(self):
        self.processor.get_auth_data_from_marqeta_client = CoroutineMock(
            return_value=["wrong wrong wrong"]
        )
        with pytest.raises(MarqetaAuthDataFormatInvalidError):
            await self.processor.record_transaction_event(
                marqeta_user_token="test_token",
                anchor_day=datetime.utcnow(),
                shift_id="123",
            )
        self.processor.get_auth_data_from_marqeta_client = CoroutineMock(
            return_value=[{"token": "test token", "card_token": "test_card_token"}]
        )
        with pytest.raises(MarqetaAuthDataFormatInvalidError):
            await self.processor.record_transaction_event(
                marqeta_user_token="test_token",
                anchor_day=datetime.utcnow(),
                shift_id="123",
            )

    async def test_record_transaction_event_existing_txn(self, mock_marqeta_auth_data):
        self.processor.get_auth_data_from_marqeta_client = CoroutineMock(
            return_value=mock_marqeta_auth_data
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=True
        )
        result = await self.processor.record_transaction_event(
            marqeta_user_token="test_token",
            anchor_day=datetime.utcnow(),
            shift_id="123",
        )
        assert result == []

    async def test_record_transaction_event_no_card_ownership(
        self, mock_marqeta_auth_data
    ):
        self.processor.get_auth_data_from_marqeta_client = CoroutineMock(
            return_value=mock_marqeta_auth_data
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=False
        )
        self.processor.card_acceptor_repo.get_or_create_card_acceptor = CoroutineMock(
            return_value=self.mock_card_acceptor
        )
        self.processor.card_ownership_repo.get_active_card_ownerships_by_card_id = CoroutineMock(
            return_value=[]
        )
        result = await self.processor.record_transaction_event(
            marqeta_user_token="test_token",
            anchor_day=datetime.utcnow(),
            shift_id="123",
        )
        assert result == []

    async def test_record_transaction_event_create_txn(self, mock_marqeta_auth_data):
        self.processor.get_auth_data_from_marqeta_client = CoroutineMock(
            return_value=mock_marqeta_auth_data
        )
        self.processor.transaction_event_repo.get_transaction_event_by_token = CoroutineMock(
            return_value=False
        )
        self.processor.card_acceptor_repo.get_or_create_card_acceptor = CoroutineMock(
            return_value=self.mock_card_acceptor
        )
        self.processor.card_ownership_repo.get_active_card_ownerships_by_card_id = CoroutineMock(
            return_value=[MagicMock(id=123), MagicMock(456)]
        )
        self.processor.transaction_event_repo.create_transaction_event = CoroutineMock(
            return_value=self.mock_transaction_event
        )
        result = await self.processor.record_transaction_event(
            marqeta_user_token="test_token",
            anchor_day=datetime.utcnow(),
            shift_id="123",
        )
        assert len(result) == 1
        validate_expected_items_in_dict(
            expected=self.expected_result.dict(), actual=result[0].dict()
        )
