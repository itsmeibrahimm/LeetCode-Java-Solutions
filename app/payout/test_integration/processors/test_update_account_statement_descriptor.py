from datetime import datetime, timezone

import pytest
import pytest_mock

from app.commons.database.infra import DB
from app.payout.core.account.processors.update_account_statement_descriptor import (
    UpdatePayoutAccountStatementDescriptorRequest,
    UpdatePayoutAccountStatementDescriptor,
)
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.repository.maindb.model.payment_account import PaymentAccountCreate
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.types import AccountType


class TestUpdatePayoutAccount:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    async def test_update_payout_account_statement_descriptor(
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
        assert created_account.statement_descriptor == "test_statement_descriptor"

        request = UpdatePayoutAccountStatementDescriptorRequest(
            payout_account_id=created_account.id,
            statement_descriptor="update_statement_descriptor",
        )

        update_account_op = UpdatePayoutAccountStatementDescriptor(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            request=request,
        )

        updated_payout_account: PayoutAccountInternal = await update_account_op._execute()
        assert (
            updated_payout_account.payment_account.statement_descriptor
            == "update_statement_descriptor"
        )
