import pytest

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
