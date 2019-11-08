import asyncio
import uuid
from datetime import datetime

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.config.app_config import AppConfig

from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeClient, StripeAsyncClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.test_integration.constants import (
    VISA_DEBIT_CARD_TOKEN,
    BANK_ACCOUNT_TOKEN,
)
from app.commons.types import Currency, CountryCode
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.account.processors.create_payout_method import (
    CreatePayoutMethod,
    CreatePayoutMethodRequest,
)
from app.payout.core.account import models as account_models
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.bankdb.model.payout_card import PayoutCard
from app.payout.repository.bankdb.model.payout_method import PayoutMethod
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
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
    mock_stripe_bank_account,
    prepare_and_insert_stripe_managed_account,
)
from app.payout.models import PayoutExternalAccountType


class TestCreatePayoutMethod:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payout_card_repo(self, payout_bankdb: DB) -> PayoutCardRepository:
        return PayoutCardRepository(database=payout_bankdb)

    @pytest.fixture
    def payout_method_repo(self, payout_bankdb: DB) -> PayoutMethodRepository:
        return PayoutMethodRepository(database=payout_bankdb)

    @pytest.fixture
    def payment_account_edit_history_repo(
        self, payout_bankdb: DB
    ) -> PaymentAccountEditHistoryRepository:
        return PaymentAccountEditHistoryRepository(database=payout_bankdb)

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

    async def test_create_payout_method_card(
        self,
        mocker: pytest_mock.MockFixture,
        payout_card_repo: PayoutCardRepository,
        payout_method_repo: PayoutMethodRepository,
        payment_account_repo: PaymentAccountRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        # 1. prepare a payout account
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        request = CreatePayoutMethodRequest(
            payout_account_id=payout_account.id,
            token=VISA_DEBIT_CARD_TOKEN,
            type=PayoutExternalAccountType.CARD,
        )

        # 2. mock a stripe_managed_account
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

        # 3. mock a created StripeCard
        stripe_card = mock_stripe_card()

        @asyncio.coroutine
        def mock_created_stripe_card(*args, **kwargs):
            return stripe_card

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_external_account",
            side_effect=mock_created_stripe_card,
        )

        # mock unset_default_and_create_payout_method_and_payout_card
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

        # CreatePayoutMethod op
        create_payout_method_op = CreatePayoutMethod(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            payout_method_miscellaneous_repo=payout_method_miscellaneous_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            request=request,
            stripe=stripe_async_client,
        )

        expected_payout_card_internal = account_models.PayoutCardInternal(
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
        payout_card_internal: account_models.PayoutCardInternal = await create_payout_method_op._execute()
        assert payout_card_internal.payout_account_id == payout_account.id
        assert payout_card_internal == expected_payout_card_internal

    async def test_create_payout_method_bank_account(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        # 1. prepare a stripe_managed_account
        stripe_managed_account = await prepare_and_insert_stripe_managed_account(
            payment_account_repo
        )

        # 2. prepare a payout account
        payout_account = await prepare_and_insert_payment_account(
            account_id=stripe_managed_account.id,
            payment_account_repo=payment_account_repo,
        )
        request = CreatePayoutMethodRequest(
            payout_account_id=payout_account.id,
            token=BANK_ACCOUNT_TOKEN,
            type=PayoutExternalAccountType.BANK_ACCOUNT,
        )

        # 3. mock a created StripeBankAccount
        stripe_bank_account = mock_stripe_bank_account()

        @asyncio.coroutine
        def mock_created_stripe_bank_account(*args, **kwargs):
            return stripe_bank_account

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_external_account",
            side_effect=mock_created_stripe_bank_account,
        )

        # 4. Call CreatePayoutMethod op
        create_payout_method_op = CreatePayoutMethod(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            payout_method_miscellaneous_repo=payout_method_miscellaneous_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            request=request,
            stripe=stripe_async_client,
        )

        expected_payout_bank_account_internal = account_models.PayoutBankAccountInternal(
            id=None,
            token=None,
            created_at=None,
            updated_at=None,
            deleted_at=None,
            payout_account_id=payout_account.id,
            currency=Currency.USD,
            country=CountryCode.US,
            bank_last4=stripe_bank_account.last4,
            bank_name=stripe_bank_account.bank_name,
            fingerprint=stripe_bank_account.fingerprint,
        )
        bank_account_internal: account_models.PayoutBankAccountInternal = await create_payout_method_op._execute()
        assert bank_account_internal.payout_account_id == payout_account.id
        print(bank_account_internal)
        print(expected_payout_bank_account_internal)
        assert bank_account_internal == expected_payout_bank_account_internal

        # 5. Fetch the latest payment_account_edit_history record
        latest_record = await payment_account_edit_history_repo.get_most_recent_bank_update(
            payment_account_id=payout_account.id
        )
        assert latest_record
        assert latest_record.payment_account_id == payout_account.id
        assert latest_record.account_id == stripe_managed_account.id
        assert latest_record.new_bank_last4 == stripe_bank_account.last4
        assert latest_record.new_bank_name == stripe_bank_account.bank_name
        assert latest_record.new_fingerprint == stripe_bank_account.fingerprint

        # 6. refresh the stripe_managed_account to verify the results
        updated_stripe_managed_account = await payment_account_repo.get_stripe_managed_account_by_id(
            stripe_managed_account.id
        )
        assert updated_stripe_managed_account
        assert (
            updated_stripe_managed_account.default_bank_name
            == stripe_bank_account.bank_name
        )
        assert (
            updated_stripe_managed_account.default_bank_last_four
            == stripe_bank_account.last4
        )

    async def test_create_payout_method_raise_error(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        payout_account = await prepare_and_insert_payment_account(payment_account_repo)
        # test payout account with no PGP account setup
        request = CreatePayoutMethodRequest(
            payout_account_id=payout_account.id,
            token=VISA_DEBIT_CARD_TOKEN,
            type=PayoutExternalAccountType.CARD,
        )
        create_payout_method_op = CreatePayoutMethod(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payout_method_miscellaneous_repo=payout_method_miscellaneous_repo,
            request=request,
            stripe=stripe_async_client,
        )
        with pytest.raises(PayoutError) as e:
            await create_payout_method_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PGP_ACCOUNT_NOT_FOUND.value]
        )

        # test payout account which is not existing
        request = CreatePayoutMethodRequest(
            payout_account_id=payout_account.id + 1,
            token=VISA_DEBIT_CARD_TOKEN,
            type=PayoutExternalAccountType.CARD,
        )
        create_payout_method_op = CreatePayoutMethod(
            logger=mocker.Mock(),
            payment_account_repo=payment_account_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            payout_method_miscellaneous_repo=payout_method_miscellaneous_repo,
            request=request,
            stripe=stripe_async_client,
        )
        with pytest.raises(PayoutError) as e:
            await create_payout_method_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.PAYOUT_ACCOUNT_NOT_FOUND.value]
        )
