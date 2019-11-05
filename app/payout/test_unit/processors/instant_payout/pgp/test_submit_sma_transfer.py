import pytest
from asynctest import MagicMock, CoroutineMock

from app.commons.core.errors import PGPConnectionError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_client import StripeClient
from app.commons.providers.stripe import stripe_models as models
from app.commons.providers.stripe.stripe_models import Amount, Currency, Destination
from app.commons.types import CountryCode
from app.payout.core.instant_payout.models import (
    SMATransferRequest,
    SMATransferResponse,
)
from app.payout.core.instant_payout.processors.pgp.submit_sma_transfer import (
    SubmitSMATransfer,
)
from app.payout.test_integration.utils import mock_transfer


class TestSubmitSMATransfer:
    pytestmark = [pytest.mark.asyncio]

    def setup(self):
        self.stripe_client = StripeClient(
            [models.StripeClientSettings(api_key="xxx", country="US")]
        )
        self.stripe_async_client = StripeAsyncClient(
            executor_pool=MagicMock(), stripe_client=self.stripe_client
        )
        self.stripe_async_client.create_transfer = CoroutineMock()

        self.request = SMATransferRequest(
            amount=Amount(100),
            currency=Currency("usd"),
            destination=Destination("acct_xxx"),
            country=CountryCode.US,
            idempotency_key="test_idempotency_key",
        )
        self.submit_sma_transfer = SubmitSMATransfer(
            self.request, self.stripe_async_client, MagicMock()
        )

    async def test_successfully_submit_sma_transfer(self):
        stripe_transfer = mock_transfer()
        self.stripe_async_client.create_transfer.return_value = stripe_transfer

        assert await self.submit_sma_transfer.execute() == SMATransferResponse(
            stripe_transfer_id=stripe_transfer.id,
            stripe_object=stripe_transfer.object,
            amount=stripe_transfer.amount,
            currency=stripe_transfer.currency,
            destination=stripe_transfer.destination,
        )

    async def test_should_raise_exception_when_stripe_return_stripe_return_exception(
        self
    ):
        self.stripe_async_client.create_transfer.side_effect = PGPConnectionError
        with pytest.raises(PGPConnectionError):
            await self.submit_sma_transfer.execute()
