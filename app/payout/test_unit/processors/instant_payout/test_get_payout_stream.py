import pytest
import pytz
from asynctest import CoroutineMock

from app.payout.core.instant_payout.models import (
    GetPayoutStreamRequest,
    GetPayoutStreamResponse,
    PayoutStreamItem,
)
from app.payout.core.instant_payout.processors.get_payout_stream import GetPayoutStream
from app.payout.repository.bankdb.model.payout import Payout
from datetime import datetime

from app.payout.repository.bankdb.model.stripe_payout_request import StripePayoutRequest


class TestGetPayoutStream:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, payout_repo, stripe_payout_request_repo):
        self.request = GetPayoutStreamRequest(payout_account_id=111, limit=2, offset=0)
        self.current_time = datetime.utcnow()
        self.payout_1 = Payout(
            id=123,
            amount=999,
            payment_account_id=self.request.payout_account_id,
            status="paid",
            currency="usd",
            fee=199,
            type="some_type",
            created_at=self.current_time,
            updated_at=self.current_time,
            idempotency_key="some_key",
            payout_method_id=1234,
            transaction_ids=[11, 22, 33],
            token="some_token",
        )
        self.payout_2 = Payout(
            id=124,
            amount=999,
            payment_account_id=self.request.payout_account_id,
            status="paid",
            currency="usd",
            fee=199,
            type="some_type",
            created_at=self.current_time,
            updated_at=self.current_time,
            idempotency_key="some_key",
            payout_method_id=1234,
            transaction_ids=[111, 212, 313],
            token="some_token",
        )
        self.stripe_payout_request_1 = StripePayoutRequest(
            id=567,
            payout_id=self.payout_1.id,
            idempotency_key="some_key",
            payout_method_id=self.payout_1.payout_method_id,
            created_at=self.current_time,
            updated_at=self.current_time,
            status="paid",
            stripe_payout_id="po_xxx_1",
        )

        self.stripe_payout_request_1_2 = StripePayoutRequest(
            id=5677,
            payout_id=self.payout_1.id,
            idempotency_key="some_key",
            payout_method_id=self.payout_1.payout_method_id,
            created_at=self.current_time,
            updated_at=self.current_time,
            status="paid",
            stripe_payout_id="po_xxx_1_2",
        )

        self.stripe_payout_request_2 = StripePayoutRequest(
            id=568,
            payout_id=self.payout_2.id,
            idempotency_key="some_key",
            payout_method_id=self.payout_2.payout_method_id,
            created_at=self.current_time,
            updated_at=self.current_time,
            status="paid",
            stripe_payout_id="po_xxx_2",
        )

        payout_repo.list_payout_by_payout_account_id = CoroutineMock()
        stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids = (
            CoroutineMock()
        )

        self.get_payout_stream_op = GetPayoutStream(
            self.request, payout_repo, stripe_payout_request_repo
        )

    async def test_get_payout_stream_return_empty_list(
        self, payout_repo, stripe_payout_request_repo
    ):
        payout_repo.list_payout_by_payout_account_id.return_value = []
        stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids.return_value = (
            []
        )

        expected = GetPayoutStreamResponse(count=0, offset=None, instant_payouts=[])
        assert await self.get_payout_stream_op.execute() == expected

    async def test_get_payout_stream_when_payout_has_one_stripe_payout_request(
        self, payout_repo, stripe_payout_request_repo
    ):
        payout_repo.list_payout_by_payout_account_id.return_value = [
            self.payout_2,
            self.payout_1,
        ]

        stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids.return_value = [
            self.stripe_payout_request_2,
            self.stripe_payout_request_1,
        ]

        payout_item_1 = PayoutStreamItem(
            payout_account_id=self.payout_1.payment_account_id,
            payout_id=self.payout_1.id,
            amount=self.payout_1.amount,
            currency=self.payout_1.currency.lower(),
            fee=self.payout_1.fee,
            status=self.payout_1.status,
            pgp_payout_id=self.stripe_payout_request_1.stripe_payout_id,
            created_at=self.payout_1.created_at.replace(tzinfo=pytz.utc),
        )

        payout_item_2 = PayoutStreamItem(
            payout_account_id=self.payout_2.payment_account_id,
            payout_id=self.payout_2.id,
            amount=self.payout_2.amount,
            currency=self.payout_2.currency.lower(),
            fee=self.payout_2.fee,
            status=self.payout_2.status,
            pgp_payout_id=self.stripe_payout_request_2.stripe_payout_id,
            created_at=self.payout_2.created_at.replace(tzinfo=pytz.utc),
        )

        expected = GetPayoutStreamResponse(
            count=2,
            offset=self.request.offset + self.request.limit,
            instant_payouts=[payout_item_2, payout_item_1],
        )
        assert await self.get_payout_stream_op.execute() == expected

    async def test_get_payout_stream_when_payout_has_multiple_stripe_payout_requests(
        self, payout_repo, stripe_payout_request_repo
    ):
        payout_repo.list_payout_by_payout_account_id.return_value = [
            self.payout_2,
            self.payout_1,
        ]

        stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids.return_value = [
            self.stripe_payout_request_1_2,
            self.stripe_payout_request_2,
            self.stripe_payout_request_1,
        ]

        # item 1 pgp_payout_id should be the one from stripe_payout_request_1_2
        payout_item_1 = PayoutStreamItem(
            payout_account_id=self.payout_1.payment_account_id,
            payout_id=self.payout_1.id,
            amount=self.payout_1.amount,
            currency=self.payout_1.currency.lower(),
            fee=self.payout_1.fee,
            status=self.payout_1.status,
            pgp_payout_id=self.stripe_payout_request_1_2.stripe_payout_id,
            created_at=self.payout_1.created_at.replace(tzinfo=pytz.utc),
        )

        payout_item_2 = PayoutStreamItem(
            payout_account_id=self.payout_2.payment_account_id,
            payout_id=self.payout_2.id,
            amount=self.payout_2.amount,
            currency=self.payout_2.currency.lower(),
            fee=self.payout_2.fee,
            status=self.payout_2.status,
            pgp_payout_id=self.stripe_payout_request_2.stripe_payout_id,
            created_at=self.payout_2.created_at.replace(tzinfo=pytz.utc),
        )

        expected = GetPayoutStreamResponse(
            count=2,
            offset=self.request.offset + self.request.limit,
            instant_payouts=[payout_item_2, payout_item_1],
        )
        assert await self.get_payout_stream_op.execute() == expected
