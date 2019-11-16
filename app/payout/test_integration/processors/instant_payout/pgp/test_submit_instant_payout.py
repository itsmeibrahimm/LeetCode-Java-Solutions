import uuid
import pytest
from asynctest import Mock, CoroutineMock

from app.commons.core.errors import PGPConnectionError
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import Amount, Destination, Currency
from app.commons.types import CountryCode
from app.payout.core.errors import InstantPayoutCardDeclineError
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
        self.amount_to_submit = 1000
        self.payout_create = PayoutCreate(
            amount=self.amount_to_submit,
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
        payout = await payout_repo.create_payout(data=self.payout_create)

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
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            amount=Amount(self.amount_to_submit),
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
            balance=self.amount_to_submit
        )

        # Submit Instant payout with amount_to_submit
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            country=CountryCode.US,
            stripe_account_id=self.connected_account_id,
            amount=self.amount_to_submit,
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

    async def test_fail_to_submit_instant_payout_due_to_sma_transfer_stripe_connection_error(
        self,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepository,
    ):
        # Insert Payout record
        payout = await payout_repo.create_payout(data=self.payout_create)

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
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            amount=Amount(self.amount_to_submit),
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
        # Mock PGPConnectionError
        error = PGPConnectionError()
        stripe_async_client.create_transfer_with_stripe_error_translation = CoroutineMock(  # type: ignore
            side_effect=error
        )

        transaction_repo.set_transaction_payout_id_by_ids = (  # type: ignore
            CoroutineMock()
        )

        with pytest.raises(PGPConnectionError):
            await submit_sma_transfer_op.execute()

        # Get payout error field
        payout = await payout_repo.get_payout_by_id(payout_id=payout.id)  # type: ignore
        assert payout is not None
        payout_error = payout.error
        assert payout_error == error.__dict__
        # Status should be error instead of failed, since it's PGPConnectionError
        assert payout.status == InstantPayoutStatusType.ERROR

        # detach transaction is called
        transaction_repo.set_transaction_payout_id_by_ids.assert_awaited_once_with(  # type: ignore
            transaction_ids=self.transaction_ids, payout_id=None
        )

    async def test_fail_to_submit_instant_payout_due_to_sma_transfer_other_error(
        self,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepository,
    ):
        # Insert Payout record
        payout = await payout_repo.create_payout(data=self.payout_create)

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
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            amount=Amount(self.amount_to_submit),
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

        # Mock Exception
        error = Exception("some error")
        stripe_async_client.create_transfer_with_stripe_error_translation = CoroutineMock(  # type: ignore
            side_effect=error
        )
        transaction_repo.set_transaction_payout_id_by_ids = (  # type: ignore
            CoroutineMock()
        )

        # Submit SMA Transfer
        with pytest.raises(Exception):
            await submit_sma_transfer_op.execute()

        # Get payout fields, status should be New
        payout = await payout_repo.get_payout_by_id(payout_id=payout.id)  # type: ignore
        assert payout.status == InstantPayoutStatusType.NEW
        assert payout.error is None

        # detach transaction is not called
        transaction_repo.set_transaction_payout_id_by_ids.assert_not_awaited()  # type: ignore

    async def test_fail_to_submit_instant_payout_due_to_submit_payout_stripe_connection_error(
        self,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepository,
    ):
        # Insert Payout record
        payout = await payout_repo.create_payout(data=self.payout_create)

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
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            amount=Amount(self.amount_to_submit),
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
        # Submit SMA Transfer
        stripe_transfer = await submit_sma_transfer_op.execute()
        assert stripe_transfer.stripe_transfer_id.startswith("tr_")
        assert stripe_transfer.stripe_object == "transfer"
        assert stripe_transfer.amount == self.sma_transfer_request.amount
        assert stripe_transfer.currency == self.sma_transfer_request.currency
        assert stripe_transfer.destination == self.sma_transfer_request.destination

        # Retrieve SMA Balance, should be amount_to_submit
        assert await sma_balance_check_op.execute() == SMABalance(
            balance=self.amount_to_submit
        )

        # Submit Instant payout with amount_to_submit
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            country=CountryCode.US,
            stripe_account_id=self.connected_account_id,
            amount=self.amount_to_submit,
            currency=Currency("usd"),
            payout_method_id=self.payout_method_id,
            destination=self.stripe_card_id,
            idempotency_key="instant-payout-{}".format(str(uuid.uuid4())),
        )

        # Mock PGPConnectionError
        error = PGPConnectionError()
        stripe_async_client.create_payout_with_stripe_error_translation = CoroutineMock(  # type: ignore
            side_effect=error
        )
        transaction_repo.set_transaction_payout_id_by_ids = (  # type: ignore
            CoroutineMock()
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request,
            stripe_client=stripe_async_client,
            stripe_payout_request_repo=stripe_payout_request_repo,
            payout_repo=payout_repo,
            transaction_repo=transaction_repo,
            logger=Mock(),
        )

        with pytest.raises(PGPConnectionError):
            await submit_instant_payout_op.execute()

        # Get payout error field
        payout = await payout_repo.get_payout_by_id(payout_id=payout.id)  # type: ignore
        payout_error = payout.error
        assert payout_error == error.__dict__
        # Status should be error instead of failed, since it's PGPConnectionError
        assert payout.status == InstantPayoutStatusType.ERROR

        # Get stripe payout request error field
        stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout.id
        )
        assert stripe_payout_request is not None
        # Status should be error instead of failed, since it's PGPConnectionError
        assert stripe_payout_request.status == InstantPayoutStatusType.ERROR
        assert stripe_payout_request.response is None
        assert stripe_payout_request.stripe_payout_id is None

        # detach transaction is called
        transaction_repo.set_transaction_payout_id_by_ids.assert_awaited_once_with(  # type: ignore
            transaction_ids=self.transaction_ids, payout_id=None
        )

    async def test_fail_to_submit_instant_payout_due_to_submit_payout_stripe_card_decline_error(
        self,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepository,
    ):
        # Insert Payout record
        payout = await payout_repo.create_payout(data=self.payout_create)

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
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            amount=Amount(self.amount_to_submit),
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
        # Submit SMA Transfer
        stripe_transfer = await submit_sma_transfer_op.execute()
        assert stripe_transfer.stripe_transfer_id.startswith("tr_")
        assert stripe_transfer.stripe_object == "transfer"
        assert stripe_transfer.amount == self.sma_transfer_request.amount
        assert stripe_transfer.currency == self.sma_transfer_request.currency
        assert stripe_transfer.destination == self.sma_transfer_request.destination

        # Retrieve SMA Balance, should be amount_to_submit
        assert await sma_balance_check_op.execute() == SMABalance(
            balance=self.amount_to_submit
        )

        # Submit Instant payout with amount_to_submit
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            country=CountryCode.US,
            stripe_account_id=self.connected_account_id,
            amount=self.amount_to_submit,
            currency=Currency("usd"),
            payout_method_id=self.payout_method_id,
            destination=self.stripe_card_id,
            idempotency_key="instant-payout-{}".format(str(uuid.uuid4())),
        )

        # Mock InstantPayoutCardDeclineError
        error = InstantPayoutCardDeclineError()
        stripe_async_client.create_payout_with_stripe_error_translation = CoroutineMock(  # type: ignore
            side_effect=error
        )
        transaction_repo.set_transaction_payout_id_by_ids = (  # type: ignore
            CoroutineMock()
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request,
            stripe_client=stripe_async_client,
            stripe_payout_request_repo=stripe_payout_request_repo,
            payout_repo=payout_repo,
            transaction_repo=transaction_repo,
            logger=Mock(),
        )

        with pytest.raises(InstantPayoutCardDeclineError):
            await submit_instant_payout_op.execute()

        # Get payout error field
        payout = await payout_repo.get_payout_by_id(payout_id=payout.id)  # type: ignore
        assert payout is not None
        payout_error = payout.error
        assert payout_error == error.__dict__
        # Status should be error instead of failed, since it's InstantPayoutCardDeclineError
        assert payout.status == InstantPayoutStatusType.FAILED

        # Get stripe payout request error field
        stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout.id
        )
        assert stripe_payout_request is not None
        # Status should be error instead of failed, since it's InstantPayoutCardDeclineError
        assert stripe_payout_request.status == InstantPayoutStatusType.FAILED
        assert stripe_payout_request.response is None
        assert stripe_payout_request.stripe_payout_id is None

        # detach transaction is called
        transaction_repo.set_transaction_payout_id_by_ids.assert_awaited_once_with(  # type: ignore
            transaction_ids=self.transaction_ids, payout_id=None
        )

    async def test_fail_to_submit_instant_payout_due_to_submit_payout_other_error(
        self,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepository,
    ):
        # Insert Payout record
        payout = await payout_repo.create_payout(data=self.payout_create)

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
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            amount=Amount(self.amount_to_submit),
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
        # Submit SMA Transfer
        stripe_transfer = await submit_sma_transfer_op.execute()
        assert stripe_transfer.stripe_transfer_id.startswith("tr_")
        assert stripe_transfer.stripe_object == "transfer"
        assert stripe_transfer.amount == self.sma_transfer_request.amount
        assert stripe_transfer.currency == self.sma_transfer_request.currency
        assert stripe_transfer.destination == self.sma_transfer_request.destination

        # Retrieve SMA Balance, should be amount_to_submit
        assert await sma_balance_check_op.execute() == SMABalance(
            balance=self.amount_to_submit
        )

        # Submit Instant payout with amount_to_submit
        submit_instant_payout_request = SubmitInstantPayoutRequest(
            payout_id=payout.id,
            transaction_ids=self.transaction_ids,
            country=CountryCode.US,
            stripe_account_id=self.connected_account_id,
            amount=self.amount_to_submit,
            currency=Currency("usd"),
            payout_method_id=self.payout_method_id,
            destination=self.stripe_card_id,
            idempotency_key="instant-payout-{}".format(str(uuid.uuid4())),
        )

        # Mock Exception
        error = Exception("some error")
        stripe_async_client.create_payout_with_stripe_error_translation = CoroutineMock(  # type: ignore
            side_effect=error
        )
        transaction_repo.set_transaction_payout_id_by_ids = (  # type: ignore
            CoroutineMock()
        )

        submit_instant_payout_op = SubmitInstantPayout(
            request=submit_instant_payout_request,
            stripe_client=stripe_async_client,
            stripe_payout_request_repo=stripe_payout_request_repo,
            payout_repo=payout_repo,
            transaction_repo=transaction_repo,
            logger=Mock(),
        )

        with pytest.raises(Exception):
            await submit_instant_payout_op.execute()

        # Get payout fields, status should be New
        payout = await payout_repo.get_payout_by_id(payout_id=payout.id)  # type: ignore
        assert payout is not None
        assert payout.status == InstantPayoutStatusType.NEW
        assert payout.error is None

        # Get stripe payout request fields, status should be New
        stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout.id
        )
        assert stripe_payout_request is not None
        # Status should be error instead of failed, since it's InstantPayoutCardDeclineError
        assert stripe_payout_request.status == InstantPayoutStatusType.NEW
        assert stripe_payout_request.response is None
        assert stripe_payout_request.stripe_payout_id is None

        # detach transaction is not called
        transaction_repo.set_transaction_payout_id_by_ids.assert_not_awaited()  # type: ignore
