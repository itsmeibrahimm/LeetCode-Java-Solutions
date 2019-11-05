import pytest
from asynctest import MagicMock, CoroutineMock

from app.commons.core.errors import PGPConnectionError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_models import (
    Amount,
    Currency,
    Destination,
    StripeAccountId,
)
from app.commons.types import CountryCode
from app.payout.core.instant_payout.models import (
    SubmitInstantPayoutRequest,
    SubmitInstantPayoutResponse,
)
from app.payout.core.instant_payout.processors.pgp.submit_instant_payout import (
    SubmitInstantPayout,
)
from app.payout.test_integration.utils import mock_payout


class TestSubmitInstantPayout:
    pytestmark = [pytest.mark.asyncio]

    def setup(self):
        self.stripe_client = StripeClient(
            [models.StripeClientSettings(api_key="xxx", country="US")]
        )
        self.stripe_async_client = StripeAsyncClient(
            executor_pool=MagicMock(), stripe_client=self.stripe_client
        )
        self.stripe_async_client.create_payout_with_stripe_error_translation = (
            CoroutineMock()
        )

        self.request = SubmitInstantPayoutRequest(
            country=CountryCode.US,
            stripe_account_id=StripeAccountId("acct_xxx"),
            amount=Amount(500),
            currency=Currency("usd"),
            destination=Destination("card_xxx"),
            idempotency_key="test_idempotency_key",
        )
        self.submit_instant_payout = SubmitInstantPayout(
            self.request, self.stripe_async_client, MagicMock()
        )

    async def test_successfully_submit_instant_payout(self):
        stripe_payout = mock_payout()
        self.stripe_async_client.create_payout_with_stripe_error_translation.return_value = (
            stripe_payout
        )

        assert await self.submit_instant_payout.execute() == SubmitInstantPayoutResponse(
            stripe_payout_id=stripe_payout.id,
            stripe_object=stripe_payout.object,
            status=stripe_payout.status,
            amount=stripe_payout.amount,
            currency=stripe_payout.currency,
            destination=stripe_payout.destination,
        )

    async def test_should_raise_exception_when_stripe_return_exception(self):
        self.stripe_async_client.create_payout_with_stripe_error_translation.side_effect = (
            PGPConnectionError
        )
        with pytest.raises(PGPConnectionError):
            await self.submit_instant_payout.execute()
