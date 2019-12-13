import asyncio
import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.account.utils import (
    get_country_shortname,
    get_account_balance,
    get_currency_code,
)
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.core.transfer.utils import get_target_metadata
from app.payout.models import PayoutTargetType

from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_managed_account,
    mock_balance,
)


class TestUtils:
    pytestmark = [pytest.mark.asyncio]

    async def test_get_country_shortname_success(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo, country_shortname="ca"
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=payment_account_repo,
        )
        assert country_shortname == "ca"

    async def test_get_country_shortname_no_payment_account(
        self, payment_account_repo: PaymentAccountRepository
    ):
        country_shortname = await get_country_shortname(
            payment_account=None, payment_account_repository=payment_account_repo
        )
        assert not country_shortname

    async def test_get_country_shortname_no_account_id(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=None
        )
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=payment_account_repo,
        )
        assert not country_shortname

    async def test_get_country_shortname_no_sma(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        @asyncio.coroutine
        def mock_get_sma(*args):
            return None

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_stripe_managed_account_by_id",
            side_effect=mock_get_sma,
        )

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        country_shortname = await get_country_shortname(
            payment_account=payment_account,
            payment_account_repository=payment_account_repo,
        )
        assert not country_shortname

    async def test_get_currency_code_unsupported_country(self):
        with pytest.raises(PayoutError) as e:
            get_currency_code(country_shortname="ABC")
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.UNSUPPORTED_COUNTRY
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.UNSUPPORTED_COUNTRY.value]
        )

    async def test_get_account_balance_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_async_client: StripeAsyncClient,
        payment_account_repo: PaymentAccountRepository,
    ):
        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )

        balance = await get_account_balance(
            stripe_managed_account=sma, stripe=stripe_async_client
        )
        assert balance == 20

    async def test_get_account_balance_no_sma(self, mocker: pytest_mock.MockFixture):
        stripe_client = mocker.Mock()
        balance = await get_account_balance(
            stripe_managed_account=None, stripe=stripe_client
        )
        assert balance == 0

    async def test_get_target_metadata_json_not_found(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        payment_account_1 = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        payment_account_2 = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        data = [
            {
                str(payment_account_2.id): {
                    "target_type": PayoutTargetType.DASHER.value,
                    "target_id": 6666,
                    "statement_descriptor": "random_statement_descriptor",
                }
            }
        ]
        mocker.patch("app.commons.runtime.runtime.get_json", return_value=data)

        target_type, target_id, statement_descriptor = get_target_metadata(
            payment_account_id=payment_account_1.id
        )
        assert target_type == PayoutTargetType.STORE.value
        assert target_id == 12345
        assert statement_descriptor == "test_statement_descriptor"

    async def test_get_target_metadata_success(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        data_key = str(payment_account.id)
        data = [
            {
                data_key: {
                    "target_type": PayoutTargetType.DASHER.value,
                    "target_id": 6666,
                    "statement_descriptor": "random_statement_descriptor",
                }
            }
        ]
        mocker.patch("app.commons.runtime.runtime.get_json", return_value=data)

        target_type, target_id, statement_descriptor = get_target_metadata(
            payment_account_id=payment_account.id
        )
        assert target_type == PayoutTargetType.DASHER.value
        assert target_id == 6666
        assert statement_descriptor == "random_statement_descriptor"
