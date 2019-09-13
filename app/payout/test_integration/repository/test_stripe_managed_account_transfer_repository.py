import pytest

from app.commons.database.infra import DB
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_stripe_managed_account_transfer,
)


class TestTransferRepository:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def stripe_managed_account_transfer_repo(
        self, payout_bankdb: DB
    ) -> StripeManagedAccountTransferRepository:
        return StripeManagedAccountTransferRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    async def test_create_stripe_managed_account_transfer_success(
        self,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare stripe_managed_account_transfer and insert, then validate content
        await prepare_and_insert_stripe_managed_account_transfer(
            sma=sma,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
        )
