from typing import Dict, Any
from uuid import uuid4

import pytest

from app.commons.database.infra import DB
from app.purchasecard.models.maindb.card_acceptor import CardAcceptor
from app.purchasecard.models.maindb.marqeta_card_ownership import MarqetaCardOwnership
from app.purchasecard.models.maindb.marqeta_transaction_event import (
    MarqetaTransactionEvent,
)
from app.purchasecard.repository.card_acceptor import CardAcceptorRepository
from app.purchasecard.repository.marqeta_card_ownership import (
    MarqetaCardOwnershipRepository,
)
from app.purchasecard.repository.marqeta_transaction_event import (
    MarqetaTransactionEventRepository,
)
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_card_ownership,
    prepare_and_insert_marqeta_transaction_event,
    prepare_and_insert_card_acceptor,
)


@pytest.mark.asyncio
class TestMarqetaTransactionRepository:
    @pytest.fixture
    def marqeta_transaction_event_repo(
        self, purchasecard_maindb: DB
    ) -> MarqetaTransactionEventRepository:
        return MarqetaTransactionEventRepository(database=purchasecard_maindb)

    @pytest.fixture
    def marqeta_card_ownership_repo(
        self, purchasecard_maindb: DB
    ) -> MarqetaCardOwnershipRepository:
        return MarqetaCardOwnershipRepository(database=purchasecard_maindb)

    @pytest.fixture
    def marqeta_card_acceptor_repo(
        self, purchasecard_maindb: DB
    ) -> CardAcceptorRepository:
        return CardAcceptorRepository(database=purchasecard_maindb)

    @pytest.fixture
    def mock_auth_data(self) -> Dict[str, Any]:
        return {
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
            "response": {"code": "0000", "memo": "Approved or completed successfully"},
            "settlement_date": "2020-01-07T00:00:00Z",
            "state": "PENDING",
            "token": "5bdf7eb7-e175-4474-8aca-a187f63e5394",
            "type": "authorization",
            "user": {"metadata": {}},
            "user_token": "4162250",
            "user_transaction_time": "2020-01-07T23:14:57Z",
        }

    @pytest.fixture
    def transaction_event_token(self):
        return str(uuid4())

    @pytest.fixture
    async def card_ownership(
        self, marqeta_card_ownership_repo: MarqetaCardOwnershipRepository
    ) -> MarqetaCardOwnership:
        return await prepare_and_insert_card_ownership(
            marqeta_card_ownership_repo=marqeta_card_ownership_repo,
            card_id="test_token",
            dasher_id=602829,
        )

    @pytest.fixture
    async def card_acceptor(
        self, marqeta_card_acceptor_repo: CardAcceptorRepository
    ) -> CardAcceptor:
        return await prepare_and_insert_card_acceptor(
            card_acceptor_repo=marqeta_card_acceptor_repo,
            mid="mid",
            name="name",
            city="city",
            zip_code=str(uuid4()),
            state="state",
        )

    @pytest.fixture
    async def transaction_event(
        self,
        transaction_event_token: str,
        marqeta_transaction_event_repo: MarqetaTransactionEventRepository,
        mock_auth_data: Dict[str, Any],
        card_ownership: MarqetaCardOwnership,
        card_acceptor: CardAcceptor,
    ) -> MarqetaTransactionEvent:
        return await prepare_and_insert_marqeta_transaction_event(
            transaction_event_repo=marqeta_transaction_event_repo,
            token=transaction_event_token,
            metadata=mock_auth_data,
            raw_type=mock_auth_data["type"],
            ownership_id=card_ownership.id,
            shift_id=1234,
            amount=1234,
            card_acceptor_id=card_acceptor.id,
        )

    async def test_create_transaction_event(
        self, transaction_event: MarqetaTransactionEvent
    ):
        assert transaction_event.id is not None

    async def test_get_transaction_event_by_token(
        self,
        transaction_event: MarqetaTransactionEvent,
        card_ownership: MarqetaCardOwnership,
        card_acceptor: CardAcceptor,
        marqeta_transaction_event_repo: MarqetaTransactionEventRepository,
        transaction_event_token: str,
    ):
        result_transaction_event = await marqeta_transaction_event_repo.get_transaction_event_by_token(
            transaction_token=transaction_event_token
        )
        assert result_transaction_event is not None
        assert result_transaction_event.id == transaction_event.id
        assert result_transaction_event.ownership_id == card_ownership.id
        assert result_transaction_event.card_acceptor_id == card_acceptor.id

        result_transaction_event = await marqeta_transaction_event_repo.get_transaction_event_by_token(
            transaction_token=str(uuid4())
        )
        assert result_transaction_event is None

    async def test_has_transaction_event_by_token(
        self,
        transaction_event_token: str,
        transaction_event: MarqetaTransactionEvent,
        marqeta_transaction_event_repo: MarqetaTransactionEventRepository,
    ):
        result = await marqeta_transaction_event_repo.has_transaction_event_for_token(
            transaction_event_token
        )
        assert result is True

        result = await marqeta_transaction_event_repo.has_transaction_event_for_token(
            str(uuid4())
        )
        assert result is False
