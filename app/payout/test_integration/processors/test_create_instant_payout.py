import asyncio

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR
from stripe.error import APIConnectionError, StripeError, RateLimitError

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeAsyncClient, StripeClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import (
    StripeClientSettings,
    Transfer,
    CountryCode,
    StripeAccountId,
)
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.transfer.create_instant_payout import (
    CreateInstantPayout,
    CreateInstantPayoutRequest,
)
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.bankdb.payout import PayoutRepository
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepository,
    StripePayoutRequestCreate,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_payment_account,
    prepare_and_insert_payout,
    prepare_and_insert_stripe_payout_request,
    mock_payout,
    mock_transfer,
    mock_balance,
)
from app.payout.models import PayoutType


async def _prepare_test_create_stripe_payout_with_exception(
    mocker: pytest_mock.MockFixture,
    payout_repo: PayoutRepository,
    payment_account_repo: PaymentAccountRepository,
    stripe_payout_request_repo: StripePayoutRequestRepository,
    stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
    stripe_async_client: StripeAsyncClient,
):
    # prepare Stripe Managed Account and insert, then validate
    sma = await prepare_and_insert_stripe_managed_account(
        payment_account_repo=payment_account_repo
    )

    # prepare and insert payment_account
    payment_account = await prepare_and_insert_payment_account(
        payment_account_repo=payment_account_repo, account_id=sma.id
    )

    # prepare payout and insert, validate data
    payout = await prepare_and_insert_payout(payout_repo=payout_repo)

    mocked_balance = mock_balance()

    @asyncio.coroutine
    def mock_retrieve_balance(*args, **kwargs):
        return mocked_balance

    mocker.patch(
        "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
        side_effect=mock_retrieve_balance,
    )

    mocked_transfer = mock_transfer()

    @asyncio.coroutine
    def mock_create_transfer(*args, **kwargs):
        return mocked_transfer

    mocker.patch(
        "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
        side_effect=mock_create_transfer,
    )

    create_instant_payout_op = CreateInstantPayout(
        stripe_payout_request_repo=stripe_payout_request_repo,
        payment_account_repo=payment_account_repo,
        stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
        stripe_async_client=stripe_async_client,
        logger=mocker.Mock(),
        request=CreateInstantPayoutRequest(
            payout_account_id=payment_account.id,
            payout_card_id=1234,
            payout_stripe_card_id="temp_stripe_card_id",
            payout_idempotency_key="temp_ide_key",
            amount=200,
            payout_type=PayoutType.INSTANT,
            payout_id=payout.id,
        ),
    )

    return payout.id, create_instant_payout_op


class TestCreateInstantPayoutUtils:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_async_client: StripeAsyncClient,
        payout_repo: PayoutRepository,
    ):
        self.payment_account_id = 123
        self.amount = 200
        self.create_instant_payout_operation = CreateInstantPayout(
            stripe_payout_request_repo=stripe_payout_request_repo,
            payment_account_repo=payment_account_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_async_client=stripe_async_client,
            logger=mocker.Mock(),
            request=CreateInstantPayoutRequest(
                payout_account_id=self.payment_account_id,
                payout_card_id=1234,
                payout_stripe_card_id="temp_stripe_card_id",
                payout_idempotency_key="temp_ide_key",
                amount=self.amount,
                payout_type=PayoutType.INSTANT,
                payout_id=123456,
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

    @pytest.fixture
    def payout_repo(self, payout_bankdb: DB) -> PayoutRepository:
        return PayoutRepository(database=payout_bankdb)

    async def test_create_sma_transfer_with_amount_success(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )

        assert sma_transfer
        assert sma_transfer.amount == self.amount
        assert sma_transfer.to_stripe_account_id == sma.stripe_id

    async def test_create_instant_payout_without_payment_account(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        @asyncio.coroutine
        def mock_get_payment_account(*args, **kwargs):
            return None

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )
        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )

    async def test_create_instant_payout_without_sma(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )

        @asyncio.coroutine
        def mock_get_payment_account(*args, **kwargs):
            return payment_account

        @asyncio.coroutine
        def mock_get_sma(*args):
            return None

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_stripe_managed_account_by_id",
            side_effect=mock_get_sma,
        )

        mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_payment_account_by_id",
            side_effect=mock_get_payment_account,
        )

        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_MANAGED_ACCOUNT.value
            ]
        )

    async def test_create_stripe_transfer_success(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )
        assert sma_transfer

        stripe_transfer_id = "acct_test_stripe_transfer"
        reversals = Transfer.Reversals(
            object="list",
            data=[],
            has_more=False,
            total_count=0,
            url="/v1/transfers/tr_1FJrsxBKMMeR8JVH7C4vtauG/reversals",
        )
        stripe_transfer = Transfer(
            id=stripe_transfer_id,
            object="transfer",
            amount=100,
            amount_reversed=0,
            balance_transaction="txn_1F3zLCBKMMeR8JVHehTbTzGO",
            created=1568768340,
            currency="aud",
            description="null",
            destination="acct_1EVmnIBKMMeR8JVH",
            destination_payment="py_FpWY3tDkEm64RD",
            livemode=False,
            metadata={},
            reversals=reversals,
            reversed=False,
            source_transaction="null",
            source_type="card",
            transfer_group="null",
        )

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            return stripe_transfer

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        response = await self.create_instant_payout_operation.create_stripe_transfer(
            stripe_managed_account=sma, sma_transfer=sma_transfer
        )

        assert response

    async def test_create_stripe_transfer_with_api_connection_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )

        json_body = {"error": {"message": "test APIError"}}
        error = APIConnectionError(
            message="test APIError",
            http_status=HTTP_500_INTERNAL_SERVER_ERROR,
            json_body=json_body,
        )

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            raise error

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation.create_stripe_transfer(
                stripe_managed_account=sma, sma_transfer=sma_transfer
            )
        assert e.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert e.value.error_code == PayoutErrorCode.API_CONNECTION_ERROR
        assert e.value.error_message == "test APIError"

    async def test_create_stripe_transfer_with_stripe_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )

        json_body = {"error": {"message": "test StripeError"}}
        error = APIConnectionError(
            message="test StripeError",
            http_status=HTTP_400_BAD_REQUEST,
            json_body=json_body,
        )

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            raise error

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation.create_stripe_transfer(
                stripe_managed_account=sma, sma_transfer=sma_transfer
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.API_CONNECTION_ERROR
        assert e.value.error_message == "test StripeError"

    async def test_create_stripe_transfer_with_other_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # create sma transfer and validate
        sma_transfer = await self.create_instant_payout_operation.create_sma_transfer_with_amount(
            stripe_managed_account=sma, amount=self.amount
        )

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            raise Exception

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        with pytest.raises(PayoutError) as e:
            await self.create_instant_payout_operation.create_stripe_transfer(
                stripe_managed_account=sma, sma_transfer=sma_transfer
            )
        assert e.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert e.value.error_code == PayoutErrorCode.OTHER_ERROR
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.OTHER_ERROR.value]
        )

    async def test_create_stripe_payout_request(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payment_account_repo: PaymentAccountRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare and insert payout, then validate
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare Stripe Managed Account and insert, then validate
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )

        payout_id = payout.id
        payout_method_id = payout.payout_method_id
        idempotency_key = payout.idempotency_key
        request = {
            "country": "US",
            "stripe_account_id": sma.stripe_id,
            "amount": 100,
            "currency": "usd",
            "method": "instant",
            "external_account_id": payout_method_id,
            "statement_descriptor": "test for instant pay",
            "idempotency_key": "instant-payout-{}".format(idempotency_key),
            "metadata": {"service_origin": "payout"},
        }
        data = StripePayoutRequestCreate(
            payout_id=payout_id,
            idempotency_key="{}-request".format(idempotency_key),
            payout_method_id=payout_method_id,
            stripe_account_id=sma.stripe_id,
            request=request,
            status="new",
        )

        stripe_payout_request = await self.create_instant_payout_operation.create_stripe_payout_request(
            data=data
        )

        assert stripe_payout_request
        assert stripe_payout_request.id

    async def test_create_stripe_payout_success(
        self, mocker: pytest_mock.MockFixture, payout_repo: PayoutRepository
    ):
        country = CountryCode.US
        stripe_account = StripeAccountId("acct_test_stripe_payout")
        mocked_payout = mock_payout()
        payout_amount = mocked_payout.amount

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )

        response = await self.create_instant_payout_operation.create_stripe_payout(
            country=country, payout_amount=payout_amount, stripe_account=stripe_account
        )
        assert response

    async def test_creat_stripe_payout_with_api_connection_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payout_repo: PayoutRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        payout_id, create_instant_payout_op = await _prepare_test_create_stripe_payout_with_exception(
            mocker=mocker,
            payout_repo=payout_repo,
            payment_account_repo=payment_account_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_async_client=stripe_async_client,
        )

        json_body = {"error": {"message": "test APIError"}}
        error = APIConnectionError(
            message="test APIError",
            http_status=HTTP_500_INTERNAL_SERVER_ERROR,
            json_body=json_body,
        )

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            raise error

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )

        with pytest.raises(PayoutError) as e:
            await create_instant_payout_op._execute()

        updated_stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout_id
        )
        assert e.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert e.value.error_code == PayoutErrorCode.API_CONNECTION_ERROR
        assert e.value.error_message == "test APIError"
        assert updated_stripe_payout_request
        assert updated_stripe_payout_request.status == "failed"
        assert updated_stripe_payout_request.received_at

    async def test_creat_stripe_payout_with_rate_limit_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payout_repo: PayoutRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        payout_id, create_instant_payout_op = await _prepare_test_create_stripe_payout_with_exception(
            mocker=mocker,
            payout_repo=payout_repo,
            payment_account_repo=payment_account_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_async_client=stripe_async_client,
        )

        json_body = {"error": {"message": "test RateLimitError"}}
        error = RateLimitError(
            message="test RateLimitError",
            http_status=HTTP_500_INTERNAL_SERVER_ERROR,
            json_body=json_body,
        )

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            raise error

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )

        with pytest.raises(PayoutError) as e:
            await create_instant_payout_op._execute()
        updated_stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout_id
        )
        assert e.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert e.value.error_code == PayoutErrorCode.RATE_LIMIT_ERROR
        assert e.value.error_message == "test RateLimitError"
        assert updated_stripe_payout_request
        assert updated_stripe_payout_request.status == "failed"
        assert updated_stripe_payout_request.received_at

    async def test_creat_stripe_payout_with_stripe_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payout_repo: PayoutRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        payout_id, create_instant_payout_op = await _prepare_test_create_stripe_payout_with_exception(
            mocker=mocker,
            payout_repo=payout_repo,
            payment_account_repo=payment_account_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_async_client=stripe_async_client,
        )

        json_body = {"error": {"message": "test StripeError"}}
        error = StripeError(
            message="test StripeError",
            http_status=HTTP_400_BAD_REQUEST,
            json_body=json_body,
        )

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            raise error

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )

        with pytest.raises(PayoutError) as e:
            await create_instant_payout_op._execute()
        updated_stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout_id
        )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_SUBMISSION_ERROR
        assert e.value.error_message == "test StripeError"
        assert updated_stripe_payout_request
        assert updated_stripe_payout_request.status == "failed"
        assert updated_stripe_payout_request.received_at

    async def test_creat_stripe_payout_with_other_error_exception(
        self,
        mocker: pytest_mock.MockFixture,
        payout_repo: PayoutRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        payout_id, create_instant_payout_op = await _prepare_test_create_stripe_payout_with_exception(
            mocker=mocker,
            payout_repo=payout_repo,
            payment_account_repo=payment_account_repo,
            stripe_payout_request_repo=stripe_payout_request_repo,
            stripe_managed_account_transfer_repo=stripe_managed_account_transfer_repo,
            stripe_async_client=stripe_async_client,
        )

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            raise Exception

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )

        with pytest.raises(PayoutError) as e:
            await create_instant_payout_op._execute()
        updated_stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout_id
        )
        assert e.value.status_code == HTTP_500_INTERNAL_SERVER_ERROR
        assert e.value.error_code == PayoutErrorCode.OTHER_ERROR
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.OTHER_ERROR.value]
        )
        assert updated_stripe_payout_request
        assert updated_stripe_payout_request.status == "failed"
        assert updated_stripe_payout_request.received_at

    async def test_update_stripe_payout_request_status_with_different_status(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        stripe_payout_request = await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        payout_status = "paid"

        await self.create_instant_payout_operation.update_stripe_payout_request_status(
            stripe_payout_request=stripe_payout_request,
            stripe_payout_status=payout_status,
        )

        updated_stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout.id
        )
        assert updated_stripe_payout_request
        assert updated_stripe_payout_request.status == payout_status
        assert updated_stripe_payout_request.received_at

    async def test_update_stripe_payout_request_status_with_same_status(
        self,
        stripe_payout_request_repo: StripePayoutRequestRepository,
        payout_repo: PayoutRepository,
    ):
        # prepare payout and insert, validate data
        payout = await prepare_and_insert_payout(payout_repo=payout_repo)

        # prepare stripe_payout_request and insert, validate data
        stripe_payout_request = await prepare_and_insert_stripe_payout_request(
            stripe_payout_request_repo=stripe_payout_request_repo, payout_id=payout.id
        )

        await self.create_instant_payout_operation.update_stripe_payout_request_status(
            stripe_payout_request=stripe_payout_request,
            stripe_payout_status=stripe_payout_request.status,
        )

        updated_stripe_payout_request = await stripe_payout_request_repo.get_stripe_payout_request_by_payout_id(
            payout_id=payout.id
        )
        assert updated_stripe_payout_request
        assert not updated_stripe_payout_request.received_at
