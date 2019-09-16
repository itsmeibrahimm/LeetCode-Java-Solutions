import pytest
import pytest_mock

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeClient
from app.payout.core.account.utils import get_country_shortname, get_account_balance
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_managed_account,
)
from app.commons.providers.stripe import stripe_models as models


class TestUtils:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture
    def payment_account_repository(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def stripe(self, request, stripe_api, app_config: AppConfig):
        stripe_api.enable_mock()
        return StripeClient(
            [
                models.StripeClientSettings(
                    api_key=app_config.STRIPE_US_SECRET_KEY.value, country="US"
                )
            ]
        )

    async def test_get_country_shortname_success(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repository, country_shortname="ca"
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=sma.id
        )
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )
        assert country_shortname == "ca"

    async def test_get_country_shortname_no_payment_account(
        self, payment_account_repository: PaymentAccountRepository
    ):
        country_shortname = await get_country_shortname(
            payment_account=None, payment_account_repository=payment_account_repository
        )
        assert not country_shortname

    async def test_get_country_shortname_no_account_id(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=None
        )
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )
        assert not country_shortname

    async def test_get_country_shortname_no_sma(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=None
        )
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )
        assert not country_shortname

    async def test_get_account_balance_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe: StripeClient,
        payment_account_repository: PaymentAccountRepository,
    ):
        source_type = models.SourceTypes(bank_account=1, card=2)
        availables = models.Balance.Available(
            amount=20, currency="usd", source_types=source_type
        )
        connect_reserves = models.Balance.ConnectReserved(
            amount=20, currency="usd", source_types=source_type
        )
        pendings = models.Balance.Pending(
            amount=20, currency="usd", source_types=source_type
        )
        mock_balance = models.Balance(
            object="obj",
            available=[availables],
            connect_reserved=[connect_reserves],
            livemode=True,
            pending=[pendings],
        )
        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeClient.retrieve_balance",
            return_value=mock_balance,
        )
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repository
        )

        balance = await get_account_balance(stripe_managed_account=sma, stripe=stripe)
        assert balance == 20

    async def test_get_account_balance_no_sma(self, mocker: pytest_mock.MockFixture):
        stripe_client = mocker.Mock()
        balance = await get_account_balance(
            stripe_managed_account=None, stripe=stripe_client
        )
        assert balance == 0
