from datetime import datetime

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
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransfer,
)
from app.payout.test_integration.utils import mock_transfer


class TestSubmitSMATransfer:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self, stripe_managed_account_transfer_repo, payout_repo, transaction_repo
    ):
        self.stripe_client = StripeClient(
            [models.StripeClientSettings(api_key="xxx", country="US")]
        )
        self.stripe_async_client = StripeAsyncClient(
            executor_pool=MagicMock(), stripe_client=self.stripe_client
        )
        self.stripe_async_client.create_transfer_with_stripe_error_translation = (
            CoroutineMock()
        )
        stripe_managed_account_transfer_repo.create_stripe_managed_account_transfer = (
            CoroutineMock()
        )
        stripe_managed_account_transfer_repo.create_stripe_managed_account_transfer.return_value = StripeManagedAccountTransfer(
            id=111,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            amount=999,
            from_stripe_account_id="acct_xxx",
            to_stripe_account_id="acct_yyy",
            token="some-token",
        )
        self.request = SMATransferRequest(
            payout_id=111,
            transaction_ids=[111, 222],
            amount=Amount(999),
            currency=Currency("usd"),
            destination=Destination("acct_yyy"),
            country=CountryCode.US,
            idempotency_key="test_idempotency_key",
        )
        self.submit_sma_transfer = SubmitSMATransfer(
            self.request,
            stripe_managed_account_transfer_repo,
            self.stripe_async_client,
            payout_repo,
            transaction_repo,
            MagicMock(),
        )

    async def test_successfully_submit_sma_transfer(self):
        stripe_transfer = mock_transfer()
        self.stripe_async_client.create_transfer_with_stripe_error_translation.return_value = (
            stripe_transfer
        )

        assert await self.submit_sma_transfer.execute() == SMATransferResponse(
            stripe_transfer_id=stripe_transfer.id,
            stripe_object=stripe_transfer.object,
            amount=stripe_transfer.amount,
            currency=stripe_transfer.currency,
            destination=stripe_transfer.destination,
        )

    async def test_should_raise_exception_when_stripe_return_exception(self):
        self.stripe_async_client.create_transfer_with_stripe_error_translation.side_effect = (
            PGPConnectionError
        )
        with pytest.raises(PGPConnectionError):
            await self.submit_sma_transfer.execute()
