import asyncio
import uuid
from datetime import datetime

import pytest
import pytest_mock

from app.commons.config.app_config import AppConfig

from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeClient, StripeAsyncClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.test_integration.constants import VISA_DEBIT_CARD_TOKEN
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.account.processors.create_payout_method import (
    CreatePayoutMethod,
    CreatePayoutMethodRequest,
)
from app.payout.core.account.types import PayoutCardInternal
from app.payout.repository.bankdb.model.payout_card import PayoutCard
from app.payout.repository.bankdb.model.payout_method import PayoutMethod
from app.payout.repository.bankdb.payout_card import PayoutCardRepository
from app.payout.repository.bankdb.payout_method import PayoutMethodRepository
from app.payout.repository.bankdb.payout_method_miscellaneous import (
    PayoutMethodMiscellaneousRepository,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    mock_stripe_card,
)
from app.payout.types import PayoutExternalAccountType


class TestCreatePayoutMethod:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payout_card_repo(self, payout_bankdb: DB) -> PayoutCardRepository:
        return PayoutCardRepository(database=payout_bankdb)

    @pytest.fixture
    def payout_method_repo(self, payout_bankdb: DB) -> PayoutMethodRepository:
        return PayoutMethodRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def payout_method_miscellaneous_repo(
        self, payout_bankdb: DB
    ) -> PayoutMethodMiscellaneousRepository:
        return PayoutMethodMiscellaneousRepository(database=payout_bankdb)

    @pytest.fixture
    def stripe_async_client(self, app_config: AppConfig):
        stripe_client = StripeClient(
            settings_list=[
                StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ],
            http_client=TimedRequestsClient(),
        )

        stripe_thread_pool = ThreadPoolHelper(
            max_workers=app_config.STRIPE_MAX_WORKERS, prefix="stripe"
        )

        stripe_async_client = StripeAsyncClient(
            executor_pool=stripe_thread_pool, stripe_client=stripe_client
        )
        yield stripe_async_client
        stripe_thread_pool.shutdown()

    async def test_create_payout_method(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        request = CreatePayoutMethodRequest(
            payout_account_id=payout_account.id,
            token=VISA_DEBIT_CARD_TOKEN,
            type=PayoutExternalAccountType.CARD,
        )

        stripe_managed_account = StripeManagedAccount(
            id=1, country_shortname="US", stripe_id="test_stripe_managed_account"
        )

        @asyncio.coroutine
        def mock_stripe_managed_account(*args, **kwargs):
            return stripe_managed_account

        mocker.patch(
            "app.payout.core.account.processors.create_payout_method.get_stripe_managed_account_by_payout_account_id",
            side_effect=mock_stripe_managed_account,
        )

        stripe_card = mock_stripe_card()

        @asyncio.coroutine
        def mock_created_stripe_card(*args, **kwargs):
            return stripe_card

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_external_account_card",
            side_effect=mock_created_stripe_card,
        )

        timestamp = datetime.utcnow()
        payout_method = PayoutMethod(
            id=1,
            type="card",
            currency="usd",
            country="US",
            payment_account_id=payout_account.id,
            created_at=timestamp,
            updated_at=timestamp,
            token=uuid.uuid4(),
        )
        payout_card = PayoutCard(
            id=1,
            stripe_card_id=stripe_card.id,
            last4=stripe_card.last4,
            brand=stripe_card.brand,
            exp_month=stripe_card.exp_month,
            exp_year=stripe_card.exp_year,
            created_at=timestamp,
            updated_at=timestamp,
            fingerprint=stripe_card.fingerprint,
        )

        @asyncio.coroutine
        def mock_created_payout_method_and_payout_card(*args, **kwargs):
            return payout_method, payout_card

        mocker.patch(
            "app.payout.repository.bankdb.payout_method_miscellaneous.PayoutMethodMiscellaneousRepository.unset_default_and_create_payout_method_and_payout_card",
            side_effect=mock_created_payout_method_and_payout_card,
        )

        create_payout_method_op = CreatePayoutMethod(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            payout_method_miscellaneous_repo=payout_method_miscellaneous_repo,
            request=request,
            stripe=stripe_async_client,
        )

        expected_default_payout_card = PayoutCardInternal(
            stripe_card_id=payout_card.stripe_card_id,
            last4=payout_card.last4,
            brand=payout_card.brand,
            exp_month=payout_card.exp_month,
            exp_year=payout_card.exp_year,
            fingerprint=payout_card.fingerprint,
            payout_account_id=payout_method.payment_account_id,
            currency=payout_method.currency,
            country=payout_method.country,
            is_default=payout_method.is_default,
            id=payout_method.id,
            token=payout_method.token,
            created_at=payout_method.created_at,
            updated_at=payout_method.updated_at,
            deleted_at=payout_method.deleted_at,
        )
        payout_card_internal: PayoutCardInternal = await create_payout_method_op._execute()
        assert payout_card_internal.payout_account_id == payout_account.id
        assert payout_card_internal == expected_default_payout_card
