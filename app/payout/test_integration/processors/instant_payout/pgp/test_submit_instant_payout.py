import uuid
import pytest
from asynctest import Mock

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
from app.payout.repository.bankdb.model.payout import PayoutCreate
from app.payout.repository.bankdb.payout import (
    PayoutRepositoryInterface,
    PayoutRepository,
)
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepository


class TestSubmitInstantPayout:

    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        verified_payout_account_with_payout_card: dict,
        payout_repo: PayoutRepository,
    ):
        self.payout_account_id = verified_payout_account_with_payout_card["id"]
        self.connected_account_id = verified_payout_account_with_payout_card[
            "pgp_external_account_id"
        ]
        self.stripe_card_id = verified_payout_account_with_payout_card["stripe_card_id"]
        self.transaction_ids = [111, 222]
        self.payout_method_id = 333

    async def test_successful_submit_sma_transfer_and_retrieve_balance(
        self,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepository,
    ):
        # Insert Payout record
        amount_to_submit = 1000
        data = PayoutCreate(
            amount=amount_to_submit,
            payment_account_id=self.payout_account_id,
            status=InstantPayoutStatusType.NEW,
            currency="USD",
            fee=199,
            type="instant",
            idempotency_key=str(uuid.uuid4()),
            payout_method_id=self.payout_method_id,
            transaction_ids=self.transaction_ids,
            token="payout-test-token",
            fee_transaction_id=10,
        )
        payout = await payout_repo.create_payout(data=data)
        self.payout_id = payout.id

        # The original balance of newly created account should be 0
        sma_balance_check_request = CheckSMABalanceRequest(
            stripe_managed_account_id=self.connected_account_id, country=CountryCode.US
        )
        sma_balance_check_op = CheckSMABalance(
            sma_balance_check_request, stripe_async_client, logger=Mock()
        )
        assert await sma_balance_check_op.execute() == SMABalance(balance=0)

        # Submit SMA Transfer with amount_to_submit
        self.sma_transfer_request = SMATransferRequest(
            payout_id=self.payout_id,
            transaction_ids=self.transaction_ids,
            amount=Amount(amount_to_submit),
            currency=Currency("usd"),
            country=CountryCode.US,
            destination=Destination(self.connected_account_id),
            idempotency_key=str(uuid.uuid4()),
        )
        submit_sma_transfer_op = SubmitSMATransfer(
            self.sma_transfer_request,
            stripe_managed_account_transfer_repo,
            stripe_async_client,
            payout_repo,
            transaction_repo,
            logger=Mock(),
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
            payout_id=self.payout_id,
            transaction_ids=self.transaction_ids,
            country=CountryCode.US,
            stripe_account_id=self.connected_account_id,
            amount=amount_to_submit,
            currency=Currency("usd"),
            payout_method_id=self.payout_method_id,
            destination=self.stripe_card_id,
            idempotency_key="instant-payout-{}".format(str(uuid.uuid4())),
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request,
            stripe_client=stripe_async_client,
            stripe_payout_request_repo=stripe_payout_request_repo,
            payout_repo=payout_repo,
            transaction_repo=transaction_repo,
            logger=Mock(),
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
