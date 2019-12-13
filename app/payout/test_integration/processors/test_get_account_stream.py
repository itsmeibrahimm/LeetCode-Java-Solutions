import pytest
import pytest_mock

from datetime import datetime, timezone
from typing import Optional

from app.payout.core.account.processors.get_account_stream import (
    GetPayoutAccountStreamRequest,
    GetPayoutAccountStream,
)
from app.payout.repository.maindb.model.payment_account import PaymentAccountCreate
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.models import AccountType


class TestGetPayoutAccountStream:
    pytestmark = [pytest.mark.asyncio]

    async def test_get_payout_account_stream_empty(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        await payment_account_repo.delete_all_payment_accounts()

        request = GetPayoutAccountStreamRequest(offset=0, limit=10)
        op = GetPayoutAccountStream(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
        )
        response = await op.execute()
        assert response.new_offset is None, "new_offset should be none for empty stream"
        assert len(response.items) == 0, "items is len=0 for empty stream"

    async def test_get_payout_account_stream_more_items(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        await payment_account_repo.delete_all_payment_accounts()

        for i in range(0, 5):
            data = PaymentAccountCreate(
                account_id=123,
                account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
                entity="dasher",
                resolve_outstanding_balance_frequency="daily",
                payout_disabled=True,
                charges_enabled=True,
                old_account_id=1234,
                upgraded_to_managed_account_at=datetime.now(timezone.utc),
                is_verified_with_stripe=True,
                transfers_enabled=True,
                statement_descriptor="test_statement_descriptor",
            )
            created_account = await payment_account_repo.create_payment_account(data)
            assert created_account.id, "id shouldn't be None"
            assert created_account.created_at, "created_at shouldn't be None"

        offset: Optional[int] = 0
        limit = 2
        expected_offset = 2
        while offset is not None:
            request = GetPayoutAccountStreamRequest(offset=offset, limit=limit)
            op = GetPayoutAccountStream(
                logger=mocker.Mock(),
                payment_account_repo=payment_account_repo,
                request=request,
            )
            response = await op.execute()

            offset = response.new_offset

            if response.new_offset is not None:
                assert response.new_offset == expected_offset, "new_offset is expected"
                assert len(response.items) == limit, "items is full"
                expected_offset += limit
            else:
                assert len(response.items) == 1, "items remainder is 1"
