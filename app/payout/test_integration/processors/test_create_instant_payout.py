import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.database.infra import DB
from app.payout.core.account.processors.create_instant_payout import (
    CreateInstantPayout,
    CreateInstantPayoutRequest,
)
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_payment_account,
)
from app.payout.types import PayoutType


class TestCreateInstantPayoutUtils:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    ):
        self.payment_account_id = 123
        self.amount = 200
        self.create_instant_payout_operation = CreateInstantPayout(
            stripe_payout_request_repo=stripe_payout_request_repo,
            payment_account_repo=payment_account_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            logger=mocker.Mock(),
            request=CreateInstantPayoutRequest(
                payout_account_id=self.payment_account_id,
                amount=self.amount,
                payout_type=PayoutType.INSTANT,
            ),
        )

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_payout_request_repo(
        self, payout_bankdb: DB
    ) -> StripePayoutRequestRepository:
        return StripePayoutRequestRepository(database=payout_bankdb)

    @pytest.fixture
    def stripe_managed_account_transfer_repo(
        self, payout_bankdb: DB
    ) -> StripeManagedAccountTransferRepository:
        return StripeManagedAccountTransferRepository(database=payout_bankdb)

    async def test_create_sma_transfer_with_amount_success(
        self,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            payment_account=payment_account, amount=self.amount
        )

        assert sma_transfer
        assert sma_transfer.amount == self.amount
        assert sma_transfer.to_stripe_account_id == sma.stripe_id

    async def test_create_sma_transfer_with_amount_without_payment(
        self,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    ):
        payment_account = None
        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation.create_sma_transfer_with_amount(
                payment_account=payment_account, amount=self.amount
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )

    async def test_create_sma_transfer_with_amount_without_sma(
        self,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo,
            account_id=self.payment_account_id,
        )
        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation.create_sma_transfer_with_amount(
                payment_account=payment_account, amount=self.amount
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT.value
            ]
        )
