import uuid
import pytest
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import Amount, Destination, Currency
from app.commons.types import CountryCode
from app.payout.core.instant_payout.models import (
    SMATransferRequest,
    CheckSMABalanceRequest,
    SMABalance,
    SubmitInstantPayoutRequest,
    InstantPayoutStatusType,
)
from app.payout.core.instant_payout.processors.pgp.check_sma_balance import (
    CheckSMABalance,
)
from app.payout.core.instant_payout.processors.pgp.submit_instant_payout import (
    SubmitInstantPayout,
)
from app.payout.core.instant_payout.processors.pgp.submit_sma_transfer import (
    SubmitSMATransfer,
)


class TestSubmitInstantPayout:

    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.fixture(autouse=True)
    def setup(self, verified_payout_account_with_payout_card: dict):
        self.connected_account_id = verified_payout_account_with_payout_card[
            "pgp_external_account_id"
        ]
        self.stripe_card_id = verified_payout_account_with_payout_card["stripe_card_id"]
        print("*****", self.connected_account_id)

    async def test_successful_submit_sma_transfer_and_retrieve_balance(
        self, stripe_async_client: StripeAsyncClient, verified_payout_account: dict
    ):
        # The original balance of newly created account should be 0
        sma_balance_check_request = CheckSMABalanceRequest(
            stripe_managed_account_id=self.connected_account_id, country=CountryCode.US
        )
        sma_balance_check_op = CheckSMABalance(
            sma_balance_check_request, stripe_async_client
        )
        assert await sma_balance_check_op.execute() == SMABalance(balance=0)

        amount_to_submit = 1000
        # Submit SMA Transfer with amount_to_submit
        self.sma_transfer_request = SMATransferRequest(
            amount=Amount(amount_to_submit),
            currency=Currency("usd"),
            country=CountryCode.US,
            destination=Destination(self.connected_account_id),
            idempotency_key=str(uuid.uuid4()),
        )
        submit_sma_transfer_op = SubmitSMATransfer(
            self.sma_transfer_request, stripe_async_client
        )
        stripe_transfer = await submit_sma_transfer_op.execute()
        assert stripe_transfer.stripe_transfer_id.startswith("tr_")
        assert stripe_transfer.stripe_object == "transfer"
        assert stripe_transfer.amount == self.sma_transfer_request.amount
        assert stripe_transfer.currency == self.sma_transfer_request.currency
        assert stripe_transfer.destination == self.sma_transfer_request.destination

        # Retrieve SMA Balance, should be amount_to_submit
        assert await sma_balance_check_op.execute() == SMABalance(
            balance=amount_to_submit
        )

        # Submit Instant payout with amount_to_submit
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            country=CountryCode.US,
            stripe_account_id=self.connected_account_id,
            amount=amount_to_submit,
            currency=Currency("usd"),
            destination=self.stripe_card_id,
            idempotency_key="instant-payout-{}".format(str(uuid.uuid4())),
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request, stripe_client=stripe_async_client
        )
        stripe_payout = await submit_instant_payout_op.execute()
        assert stripe_payout.stripe_payout_id.startswith("po_")
        assert stripe_payout.stripe_object == "payout"
        assert stripe_payout.status == InstantPayoutStatusType.PENDING
        assert stripe_payout.amount == submit_instant_payout_request.amount
        assert stripe_payout.currency == submit_instant_payout_request.currency
        assert stripe_payout.destination == submit_instant_payout_request.destination

        # Retrieve SMA Balance again, should be 0
        assert await sma_balance_check_op.execute() == SMABalance(balance=0)
