import asyncio
from datetime import datetime, timezone

import pytest
import pytest_mock
from IPython.utils.tz import utcnow

from app.commons.database.infra import DB
from app.payout.core.account.processors.get_account import (
    GetPayoutAccountRequest,
    GetPayoutAccount,
)
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.core.exceptions import (
    payout_account_not_found_error,
    PayoutErrorCode,
    payout_error_message_maps,
    PayoutError,
)
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccountCreate,
    PaymentAccount,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.types import AccountType


class TestGetPayoutAccount:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    async def test_get_payout_account(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
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

        request = GetPayoutAccountRequest(payout_account_id=created_account.id)
        payment_account = PaymentAccount(
            id=data.account_id,
            account_type=data.account_type,
            entity=data.entity,
            resolve_outstanding_balance_frequency=data.resolve_outstanding_balance_frequency,
            payout_disabled=data.payout_disabled,
            charges_enabled=data.charges_enabled,
            old_account_id=data.old_account_id,
            upgraded_to_managed_account_at=data.upgraded_to_managed_account_at,
            is_verified_with_stripe=data.is_verified_with_stripe,
            transfers_enabled=data.transfers_enabled,
            statement_descriptor=data.statement_descriptor,
            created_at=utcnow(),
        )

        get_account_op = GetPayoutAccount(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
        )

        @asyncio.coroutine
        def mock_get_payment_account(*args):
            return payment_account

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )
        get_payout_account: PayoutAccountInternal = await get_account_op._execute()
        assert get_payout_account.payment_account.id == data.account_id
        assert (
            get_payout_account.payment_account.statement_descriptor
            == data.statement_descriptor
        )

        get_error = payout_account_not_found_error()
        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=get_error,
        )
        with pytest.raises(PayoutError) as e:
            await get_account_op._execute()
        assert e.value.error_code == PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND.value]
        )
