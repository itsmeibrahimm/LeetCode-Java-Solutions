from datetime import datetime

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
from app.payout.repository.bankdb.model.stripe_payout_request import StripePayoutRequest
from app.payout.test_integration.utils import mock_payout


class TestSubmitInstantPayout:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, stripe_payout_request_repo, payout_repo, transaction_repo):
        self.stripe_client = StripeClient(
            [models.StripeClientSettings(api_key="xxx", country="US")]
        )
        self.stripe_async_client = StripeAsyncClient(
            executor_pool=MagicMock(), stripe_client=self.stripe_client
        )
        self.stripe_async_client.create_payout_with_stripe_error_translation = (
            CoroutineMock()
        )

        stripe_payout_request_repo.create_stripe_payout_request = CoroutineMock()
        stripe_payout_request_repo.create_stripe_payout_request.return_value = StripePayoutRequest(
            id=11,
            payout_id=111,
            idempotency_key="test-key",
            payout_method_id=111,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            status="new",
        )
        payout_repo.update_payout_by_id = CoroutineMock()
        stripe_payout_request_repo.update_stripe_payout_request_by_id = CoroutineMock()
        transaction_repo.set_transaction_payout_id_by_ids = CoroutineMock()
        self.request = SubmitInstantPayoutRequest(
            payout_id=111,
            transaction_ids=[111, 222],
            country=CountryCode.US,
            stripe_account_id=StripeAccountId("acct_xxx"),
            amount=Amount(500),
            currency=Currency("usd"),
            payout_method_id=333,
            destination=Destination("card_xxx"),
            idempotency_key="test_idempotency_key",
        )
        self.submit_instant_payout = SubmitInstantPayout(
            self.request,
            self.stripe_async_client,
            stripe_payout_request_repo,
            payout_repo,
            transaction_repo,
            MagicMock(),
        )

    async def test_successfully_submit_instant_payout(
        self, stripe_payout_request_repo, payout_repo
    ):

        payout_repo.update_payout_by_id.return_value = None
        stripe_payout_request_repo.update_stripe_payout_request_by_id.return_value = (
            None
        )
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

    async def test_should_raise_exception_when_stripe_return_exception(
        self, transaction_repo
    ):
        transaction_repo.set_transaction_payout_id_by_ids.return_value = None
        self.stripe_async_client.create_payout_with_stripe_error_translation.side_effect = (
            PGPConnectionError
        )
        with pytest.raises(PGPConnectionError):
            await self.submit_instant_payout.execute()
