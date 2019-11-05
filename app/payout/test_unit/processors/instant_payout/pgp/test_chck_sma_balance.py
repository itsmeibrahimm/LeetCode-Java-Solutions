import pytest
from asynctest import MagicMock, CoroutineMock
from stripe import Balance

from app.commons.core.errors import PGPAuthenticationError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.stripe import stripe_models as models
from app.commons.types import CountryCode
from app.payout.core.instant_payout.models import CheckSMABalanceRequest, SMABalance
from app.payout.core.instant_payout.processors.pgp.check_sma_balance import (
    CheckSMABalance,
)
from app.payout.test_integration.utils import mock_balance


class TestCheckSMABalance:
    pytestmark = [pytest.mark.asyncio]

    def setup(self):
        self.stripe_client = StripeClient(
            [models.StripeClientSettings(api_key="xxx", country="US")]
        )
        self.stripe_async_client = StripeAsyncClient(
            executor_pool=MagicMock(), stripe_client=self.stripe_client
        )
        self.stripe_async_client.retrieve_balance_with_stripe_error_translation = (
            CoroutineMock()
        )

        self.request = CheckSMABalanceRequest(
            stripe_managed_account_id="acct_xxx", country=CountryCode.US
        )
        self.check_sma_balance = CheckSMABalance(self.request, self.stripe_async_client)

    async def test_successfully_get_balance(self):
        stripe_balance = mock_balance()
        self.stripe_async_client.retrieve_balance_with_stripe_error_translation.return_value = (
            stripe_balance
        )

        assert await self.check_sma_balance.execute() == SMABalance(
            balance=stripe_balance.available[0].amount
        )

    async def test_should_return_0_when_stripe_balance_index_error(self):
        stripe_balance = mock_balance()
        # make available of stripe_balance as empty list (raise IndexError)
        stripe_balance.available = []
        self.stripe_async_client.retrieve_balance_with_stripe_error_translation.return_value = (
            stripe_balance
        )
        assert await self.check_sma_balance.execute() == SMABalance(balance=0)

    async def test_should_return_0_when_stripe_balance_key_error(self):
        stripe_balance = Balance()
        # make available of stripe_balance as empty list (raise AttributeError)
        self.stripe_async_client.retrieve_balance_with_stripe_error_translation.return_value = (
            stripe_balance
        )
        assert await self.check_sma_balance.execute() == SMABalance(balance=0)

    async def test_should_raise_pgp_authentication_error(self):
        self.stripe_async_client.retrieve_balance_with_stripe_error_translation.side_effect = (
            PGPAuthenticationError
        )
        # Should bubble the same error
        with pytest.raises(PGPAuthenticationError):
            await self.check_sma_balance.execute()
