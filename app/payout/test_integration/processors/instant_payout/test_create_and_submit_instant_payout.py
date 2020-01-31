import hashlib
import pytest
import pytest_mock
from aioredlock import LockError
from aioredlock.redis import Redis
from asynctest import Mock

from app.commons.context.app_context import AppContext
from app.commons.core.errors import PaymentLockAcquireError
from app.commons.lock.models import GetLockRequest, LockStatus
from app.commons.operational_flags import ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.conftest import RuntimeSetter
from app.main import config
from app.payout.core.instant_payout.models import (
    CreateAndSubmitInstantPayoutRequest,
    InstantPayoutFees,
)
from app.payout.core.instant_payout.processor import InstantPayoutProcessors
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.paymentdb.payout_lock import PayoutLockRepository
from app.payout.test_integration.utils import prepare_and_insert_transaction


class TestCreateAndSubmitInstantPayout:

    pytestmark = [pytest.mark.asyncio, pytest.mark.external]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        verified_payout_account_with_payout_card: dict,
        payout_repo: PayoutRepository,
    ):
        self.payout_account_id = verified_payout_account_with_payout_card["id"]
        self.stripe_card_id = verified_payout_account_with_payout_card["stripe_card_id"]
        self.amount_to_submit = 1000
        self.mocker = mocker

    async def test_successful_create_and_submit_instant_payout_when_payment_db_lock_enabled(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_repo: PayoutRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        transaction_repo: TransactionRepository,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        payout_lock_repo: PayoutLockRepository,
        runtime_setter: RuntimeSetter,
        app_context: AppContext,
        verified_payout_account_with_payout_card: dict,
    ):
        payout_account_id = verified_payout_account_with_payout_card["id"]
        stripe_card_id = verified_payout_account_with_payout_card["stripe_card_id"]
        amount_to_submit = 1000

        # mock feature_flag
        data = {"enable_all": False, "white_list": [payout_account_id], "bucket": 0}
        runtime_setter.set(ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, data)

        # prepare transaction for payout account
        await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=payout_account_id
        )

        # create and submit instant payout
        create_and_submit_instant_payout_request = CreateAndSubmitInstantPayoutRequest(
            payout_account_id=payout_account_id,
            amount=amount_to_submit,
            currency="usd",
            card=stripe_card_id,
        )
        instant_payout_processor = InstantPayoutProcessors(
            logger=Mock(),
            payout_account_repo=payment_account_repo,
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payout_repo=payout_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            transaction_repo=transaction_repo,
            stripe=stripe_async_client,
            payment_lock_manager=app_context.redis_lock_manager,
            payout_lock_repo=payout_lock_repo,
        )

        internal_instant_payout_response = await instant_payout_processor.create_and_submit_instant_payout(
            create_and_submit_instant_payout_request
        )
        assert internal_instant_payout_response
        assert internal_instant_payout_response.payout_account_id == payout_account_id
        assert internal_instant_payout_response.payout_id
        assert (
            internal_instant_payout_response.amount
            == amount_to_submit - InstantPayoutFees.STANDARD_FEE
        )
        assert internal_instant_payout_response.fee == InstantPayoutFees.STANDARD_FEE
        payment_db_lock_id = hashlib.sha256(
            str(payout_account_id).encode("utf-8")
        ).hexdigest()
        lock_internal = await payout_lock_repo.get_lock(
            GetLockRequest(lock_id=payment_db_lock_id)
        )
        assert lock_internal
        assert lock_internal.status == LockStatus.OPEN

    async def test_successful_create_and_submit_instant_payout_when_redis_lock_enabled(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_repo: PayoutRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        transaction_repo: TransactionRepository,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        payout_lock_repo: PayoutLockRepository,
        runtime_setter: RuntimeSetter,
        app_context: AppContext,
    ):
        # mock feature_flag
        data = {"enable_all": False, "white_list": [], "bucket": 0}
        runtime_setter.set(ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, data)

        # prepare transaction for payout account
        await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=self.payout_account_id
        )

        # create and submit instant payout
        create_and_submit_instant_payout_request = CreateAndSubmitInstantPayoutRequest(
            payout_account_id=self.payout_account_id,
            amount=self.amount_to_submit,
            currency="usd",
            card=self.stripe_card_id,
        )
        instant_payout_processor = InstantPayoutProcessors(
            logger=Mock(),
            payout_account_repo=payment_account_repo,
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payout_repo=payout_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            transaction_repo=transaction_repo,
            stripe=stripe_async_client,
            payment_lock_manager=app_context.redis_lock_manager,
            payout_lock_repo=payout_lock_repo,
        )

        internal_instant_payout_response = await instant_payout_processor.create_and_submit_instant_payout(
            create_and_submit_instant_payout_request
        )
        assert internal_instant_payout_response
        assert (
            internal_instant_payout_response.payout_account_id == self.payout_account_id
        )
        assert internal_instant_payout_response.payout_id
        assert (
            internal_instant_payout_response.amount
            == self.amount_to_submit - InstantPayoutFees.STANDARD_FEE
        )
        assert internal_instant_payout_response.fee == InstantPayoutFees.STANDARD_FEE
        payment_db_lock_id = hashlib.sha256(
            str(self.payout_account_id).encode("utf-8")
        ).hexdigest()
        lock_internal = await payout_lock_repo.get_lock(
            GetLockRequest(lock_id=payment_db_lock_id)
        )
        assert not lock_internal

    async def test_create_and_submit_instant_payout_when_redis_lock_enabled_throw_exception(
        self,
        payment_account_repo: PaymentAccountRepository,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payout_repo: PayoutRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        transaction_repo: TransactionRepository,
        stripe_async_client: StripeAsyncClient,
        verified_payout_account: dict,
        payout_lock_repo: PayoutLockRepository,
        runtime_setter: RuntimeSetter,
        app_context: AppContext,
        mock_set_lock,
    ):
        # mock feature_flag
        data = {"enable_all": False, "white_list": [], "bucket": 0}
        runtime_setter.set(ENABLED_PAYMENT_DB_LOCK_FOR_PAYOUT, data)

        mock_create_payout_and_attach_to_txns = self.mocker.patch(
            "app.payout.repository.bankdb.payout.PayoutRepository.create_payout_and_attach_to_transactions"
        )
        # overwrite redis instances to some unknown address
        app_context.redis_lock_manager.redis = Redis(
            [("unknown_address", 1111)], config.REDIS_LOCK_DEFAULT_TIMEOUT
        )
        # Should raise PaymentLockAcquireError when can't connect to redis
        mock_set_lock.side_effect = LockError

        # prepare transaction for payout account
        await prepare_and_insert_transaction(
            transaction_repo=transaction_repo, payout_account_id=self.payout_account_id
        )

        # create and submit instant payout
        create_and_submit_instant_payout_request = CreateAndSubmitInstantPayoutRequest(
            payout_account_id=self.payout_account_id,
            amount=self.amount_to_submit,
            currency="usd",
            card=self.stripe_card_id,
        )
        instant_payout_processor = InstantPayoutProcessors(
            logger=Mock(),
            payout_account_repo=payment_account_repo,
            payout_card_repo=payout_card_repo,
            payout_method_repo=payout_method_repo,
            payout_repo=payout_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            transaction_repo=transaction_repo,
            stripe=stripe_async_client,
            payment_lock_manager=app_context.redis_lock_manager,
            payout_lock_repo=payout_lock_repo,
        )

        with pytest.raises(PaymentLockAcquireError):
            await instant_payout_processor.create_and_submit_instant_payout(
                create_and_submit_instant_payout_request
            )
        mock_create_payout_and_attach_to_txns.assert_not_called()
