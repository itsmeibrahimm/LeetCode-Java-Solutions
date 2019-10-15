import asyncio
import uuid

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.config.app_config import AppConfig
from app.commons.database.infra import DB
from app.commons.providers.stripe.stripe_client import StripeClient, StripeAsyncClient
from app.commons.providers.stripe.stripe_http_client import TimedRequestsClient
from app.commons.providers.stripe.stripe_models import StripeClientSettings
from app.commons.utils.pool import ThreadPoolHelper
from app.payout.core.transfer.create_standard_payout import (
    CreateStandardPayout,
    CreateStandardPayoutRequest,
)
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_stripe_transfer,
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_managed_account,
    prepare_and_insert_managed_account_transfer,
    mock_transfer,
    mock_payout,
    construct_stripe_error,
    mock_balance,
)
from app.payout.types import (
    PayoutType,
    ManagedAccountTransferStatus,
    StripeTransferSubmissionStatus,
    StripeErrorCode,
    STRIPE_TRANSFER_FAILED_STATUS,
    PayoutTargetType,
)


class TestCreateStandardPayout:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        self.payment_account_id = 1234567894
        self.create_standard_payout_operation = CreateStandardPayout(
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            logger=mocker.Mock(),
            stripe=stripe,
            request=CreateStandardPayoutRequest(
                payout_account_id=self.payment_account_id,
                amount=200,
                transfer_id="1234",
                statement_descriptor="statement_descriptor",
                payout_type=PayoutType.STANDARD,
            ),
        )

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def managed_account_transfer_repo(
        self, payout_maindb: DB
    ) -> ManagedAccountTransferRepository:
        return ManagedAccountTransferRepository(database=payout_maindb)

    @pytest.fixture()
    def stripe(self, app_config: AppConfig):
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

    async def test_create_standard_payout_success(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        stripe: StripeAsyncClient,
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )

        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=payment_account.id
        )
        request = CreateStandardPayoutRequest(
            transfer_id=str(transfer.id),
            payout_account_id=payment_account.id,
            statement_descriptor="statement_descriptor",
            amount=100,
            target_type=PayoutTargetType.DASHER,
            target_id="12345",
        )
        create_payout_op = CreateStandardPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )

        mocked_transfer = mock_transfer()

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            return mocked_transfer

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )
        await create_payout_op._execute()

    async def test_create_standard_payout_invalid_payment_account_id_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        request = CreateStandardPayoutRequest(
            transfer_id="123",
            payout_account_id=-1,
            amount=100,
            statement_descriptor="statement_descriptor",
        )
        create_payout_op = CreateStandardPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )
        with pytest.raises(PayoutError) as e:
            await create_payout_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID.value
            ]
        )

    async def test_create_standard_payout_invalid_payment_account_type_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_type=None
        )
        request = CreateStandardPayoutRequest(
            transfer_id="123",
            payout_account_id=payment_account.id,
            amount=100,
            statement_descriptor="statement_descriptor",
        )
        create_payout_op = CreateStandardPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )
        with pytest.raises(PayoutError) as e:
            await create_payout_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_ACCOUNT.value]
        )

    async def test_create_standard_payout_transfer_process_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        stripe: StripeAsyncClient,
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)

        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_status="pending",
        )
        request = CreateStandardPayoutRequest(
            transfer_id=str(transfer.id),
            payout_account_id=payment_account.id,
            statement_descriptor="statement_descriptor",
            amount=100,
        )
        create_payout_op = CreateStandardPayout(
            request=request,
            stripe_transfer_repo=stripe_transfer_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_repo=payment_account_repo,
            stripe=stripe,
            logger=mocker.Mock(),
        )
        with pytest.raises(PayoutError) as e:
            await create_payout_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_PROCESSING
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.TRANSFER_PROCESSING.value]
        )

    async def test_is_processing_or_processed_for_stripe_found_transfers(
        self,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        # prepare and insert transfer and stripe_transfer
        transfer = await prepare_and_insert_transfer(
            transfer_repo=transfer_repo, payment_account_id=self.payment_account_id
        )
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo, transfer_id=transfer.id
        )

        assert await self.create_standard_payout_operation.is_processing_or_processed_for_method(
            transfer_id=transfer.id
        )

    async def test_is_processing_or_processed_for_stripe_transfers_not_exist(self):
        assert not await self.create_standard_payout_operation.is_processing_or_processed_for_method(
            transfer_id=-1
        )

    async def test_has_stripe_managed_account_success(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        assert await self.create_standard_payout_operation.has_stripe_managed_account(
            payment_account=payment_account
        )

    async def test_has_stripe_managed_account_payment_account_without_account_id(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=None
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.has_stripe_managed_account(
                payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )

    async def test_has_stripe_managed_account_no_sma(
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
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.has_stripe_managed_account(
                payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )

    async def test_validate_payment_account_of_managed_account_transfer_success(
        self,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert await self.create_standard_payout_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account, managed_account_transfer=ma_transfer
        )

    async def test_validate_payment_account_of_managed_account_transfer_no_managed_account_transfer(
        self,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        assert await self.create_standard_payout_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account, managed_account_transfer=None
        )

    async def test_validate_payment_account_of_managed_account_transfer_id_not_equal(
        self,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=111,
            transfer_id=transfer.id,
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.validate_payment_account_of_managed_account_transfer(
                payment_account=payment_account, managed_account_transfer=ma_transfer
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.MISMATCHED_TRANSFER_PAYMENT_ACCOUNT
        assert (
            e.value.error_message
            == f"Transfer: {payment_account.id}; Managed Account Transfer: {ma_transfer.payment_account_id}"
        )

    async def test_get_stripe_account_id_success(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        stripe_id = await self.create_standard_payout_operation.get_stripe_account_id(
            payment_account=payment_account
        )
        assert stripe_id

    async def test_get_stripe_account_id_no_account_id(
        self, payment_account_repo: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=None
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.get_stripe_account_id(
                payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_ACCOUNT.value]
        )

    async def test_get_stripe_account_id_no_sma(
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
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.get_stripe_account_id(
                payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_ACCOUNT.value]
        )

    async def test_extract_failure_code_from_exception_message_success(self):
        msg = "Sorry, you don't have any external accounts in that currency (usd)"
        failure_msg = self.create_standard_payout_operation.extract_failure_code_from_exception_message(
            message=msg
        )
        assert failure_msg == "no_external_account_in_currency"

    async def test_extract_failure_code_from_exception_message_no_msg(self):
        error_msg = self.create_standard_payout_operation.extract_failure_code_from_exception_message(
            message=None
        )
        assert error_msg == "err"

    async def test_extract_failure_code_from_exception_message_msg_not_match(self):
        msg = "I am a piece of random message"
        error_msg = self.create_standard_payout_operation.extract_failure_code_from_exception_message(
            message=msg
        )
        assert error_msg == "err"

    async def test_submit_stripe_transfer_success(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        # mocked out create_for_managed_account
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            return mocked_payout

        mocker.patch(
            "app.payout.core.transfer.create_standard_payout.CreateStandardPayout.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        await self.create_standard_payout_operation.submit_stripe_transfer(
            transfer_id=transfer.id,
            payment_account=payment_account,
            amount=100,
            statement_descriptor="statement_descriptor",
            target_type=PayoutTargetType.DASHER,
            target_id="target_id",
            stripe=stripe,
        )
        retrieved_stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.stripe_status == mocked_payout.status
        assert retrieved_stripe_transfer.stripe_account_id == sma.stripe_id
        assert (
            retrieved_stripe_transfer.stripe_account_type
            == payment_account.account_type
        )
        assert retrieved_stripe_transfer.stripe_id == mocked_payout.id
        assert (
            retrieved_stripe_transfer.submission_status
            == StripeTransferSubmissionStatus.SUBMITTED
        )
        assert retrieved_stripe_transfer.submitted_at

    async def test_submit_stripe_transfer_with_stripe_id_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        # mock out create_stripe_transfer with a non-empty stripe_id so _submit_stripe_transfer will raise exception
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)

        mock_stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )

        @asyncio.coroutine
        def mock_create_stripe_transfer(*args, **kwargs):
            return mock_stripe_transfer

        mocker.patch(
            "app.payout.repository.maindb.stripe_transfer.StripeTransferRepository.create_stripe_transfer",
            side_effect=mock_create_stripe_transfer,
        )

        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                statement_descriptor="statement_descriptor",
                target_type=PayoutTargetType.DASHER,
                target_id="target_id",
                stripe=stripe,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.DUPLICATE_STRIPE_TRANSFER
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.DUPLICATE_STRIPE_TRANSFER.value
            ]
        )

    async def test_submit_stripe_transfer_no_external_account_in_currency(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        error = construct_stripe_error(code=StripeErrorCode.NO_EXT_ACCOUNT_IN_CURRENCY)

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        mocker.patch(
            "app.payout.core.transfer.create_standard_payout.CreateStandardPayout.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                statement_descriptor="statement_descriptor",
                target_type=PayoutTargetType.DASHER,
                target_id="target_id",
                stripe=stripe,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_PAYOUT_ACCT_MISSING
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert retrieved_stripe_transfer
        assert (
            retrieved_stripe_transfer.submission_error_code
            == StripeErrorCode.NO_EXT_ACCOUNT_IN_CURRENCY
        )
        assert retrieved_stripe_transfer.stripe_account_id == sma.stripe_id
        assert (
            retrieved_stripe_transfer.stripe_account_type
            == payment_account.account_type
        )
        assert retrieved_stripe_transfer.stripe_status == STRIPE_TRANSFER_FAILED_STATUS
        assert not retrieved_stripe_transfer.stripe_request_id
        assert (
            retrieved_stripe_transfer.submission_status
            == StripeTransferSubmissionStatus.FAILED_TO_SUBMIT
        )
        assert retrieved_stripe_transfer.submission_error_type == "error_type"

    async def test_submit_stripe_transfer_payout_not_allowed(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        error = construct_stripe_error(code=StripeErrorCode.PAYOUT_NOT_ALLOWED)

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        mocker.patch(
            "app.payout.core.transfer.create_standard_payout.CreateStandardPayout.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                statement_descriptor="statement_descriptor",
                target_type=PayoutTargetType.DASHER,
                target_id="target_id",
                stripe=stripe,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_PAYOUT_DISALLOWED
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert retrieved_stripe_transfer
        assert (
            retrieved_stripe_transfer.submission_error_code
            == StripeErrorCode.PAYOUT_NOT_ALLOWED
        )
        assert retrieved_stripe_transfer.stripe_account_id == sma.stripe_id
        assert (
            retrieved_stripe_transfer.stripe_account_type
            == payment_account.account_type
        )
        assert retrieved_stripe_transfer.stripe_status == STRIPE_TRANSFER_FAILED_STATUS
        assert not retrieved_stripe_transfer.stripe_request_id
        assert (
            retrieved_stripe_transfer.submission_status
            == StripeTransferSubmissionStatus.FAILED_TO_SUBMIT
        )
        assert retrieved_stripe_transfer.submission_error_type == "error_type"

    async def test_submit_stripe_transfer_invalid_request_error(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        error = construct_stripe_error(error_type=StripeErrorCode.INVALID_REQUEST_ERROR)

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        mocker.patch(
            "app.payout.core.transfer.create_standard_payout.CreateStandardPayout.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                statement_descriptor="statement_descriptor",
                target_type=PayoutTargetType.DASHER,
                target_id="target_id",
                stripe=stripe,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_INVALID_REQUEST_ERROR
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.submission_error_code == "error_code"
        assert retrieved_stripe_transfer.stripe_account_id == sma.stripe_id
        assert (
            retrieved_stripe_transfer.stripe_account_type
            == payment_account.account_type
        )
        assert retrieved_stripe_transfer.stripe_status == STRIPE_TRANSFER_FAILED_STATUS
        assert not retrieved_stripe_transfer.stripe_request_id
        assert (
            retrieved_stripe_transfer.submission_status
            == StripeTransferSubmissionStatus.FAILED_TO_SUBMIT
        )
        assert (
            retrieved_stripe_transfer.submission_error_type
            == StripeErrorCode.INVALID_REQUEST_ERROR
        )

    async def test_submit_stripe_transfer_other_exception(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe: StripeAsyncClient,
    ):
        error = construct_stripe_error(code="random_exception")

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        mocker.patch(
            "app.payout.core.transfer.create_standard_payout.CreateStandardPayout.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                statement_descriptor="statement_descriptor",
                target_type=PayoutTargetType.DASHER,
                target_id="target_id",
                stripe=stripe,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_SUBMISSION_ERROR
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert retrieved_stripe_transfer
        assert retrieved_stripe_transfer.submission_error_code == "random_exception"
        assert retrieved_stripe_transfer.stripe_account_id == sma.stripe_id
        assert (
            retrieved_stripe_transfer.stripe_account_type
            == payment_account.account_type
        )
        assert retrieved_stripe_transfer.stripe_status == STRIPE_TRANSFER_FAILED_STATUS
        assert not retrieved_stripe_transfer.stripe_request_id
        assert (
            retrieved_stripe_transfer.submission_status
            == StripeTransferSubmissionStatus.FAILED_TO_SUBMIT
        )
        assert retrieved_stripe_transfer.submission_error_type == "error_type"

    async def test_managed_account_balance_check_dasher_negative_amount_with_ma_transfer(
        self,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        # given dasher account and negative amount to create transfer, if ma_transfer for this account exists, only update its amount to 0
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert not ma_transfer.amount == 0
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=-100,
            stripe=stripe,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            managed_account_transfer_id=ma_transfer.id
        )
        # check that ma_transfer.amount is updated
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 0

    async def test_managed_account_balance_check_store_negative_amount_with_ma_transfer(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # given store account and negative amount to create transfer, if ma_transfer for this account exists, only update its amount to 0
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, entity="store", account_id=sma.id
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert not ma_transfer.amount == 0
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=10,
            stripe=stripe,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            managed_account_transfer_id=ma_transfer.id
        )
        # check that ma_transfer.amount is updated
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 0

    async def test_managed_account_balance_check_dasher_negative_amount_without_ma_transfer(
        self,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        # given dasher account and negative amount to create transfer, if ma_transfer not exist, nothing will be created/updated
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=-100,
            stripe=stripe,
        )
        assert not await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer.id
        )

    async def test_managed_account_balance_check_store_negative_amount_without_ma_transfer(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # given store account and negative amount to create transfer, if ma_transfer not exist, nothing will be created/updated
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, entity="store", account_id=sma.id
        )
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=10,
            stripe=stripe,
        )
        assert not await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer.id
        )

    async def test_managed_account_balance_check_dasher_positive_amount_with_ma_transfer_need_more_balance(
        self,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        # given dasher account and positive amount to create transfer, if ma_transfer exists and amount still needed > ma_transfer.amount, update ma_transfer amount
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert not ma_transfer.amount == 0
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=3000,
            stripe=stripe,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            managed_account_transfer_id=ma_transfer.id
        )
        # check that ma_transfer.amount is updated
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 3000

    async def test_managed_account_balance_check_store_positive_amount_with_ma_transfer_need_more_balance(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # given store account and positive amount to create transfer, if ma_transfer exists and amount still needed > ma_transfer.amount, update ma_transfer amount
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, entity="store", account_id=sma.id
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert not ma_transfer.amount == 0
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=3000,
            stripe=stripe,
        )  # amount_still_needed = 2980
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            managed_account_transfer_id=ma_transfer.id
        )
        # check that ma_transfer.amount is updated
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 2980

    async def test_managed_account_balance_check_dasher_positive_amount_with_ma_transfer_not_need_more_balance(
        self,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        # given dasher account and positive amount to create transfer, if ma_transfer exists and amount still needed <= ma_transfer.amount, nothing will be created/updated
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert not ma_transfer.amount == 0
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=1000,
            stripe=stripe,
        )
        assert (
            ma_transfer
            == await managed_account_transfer_repo.get_managed_account_transfer_by_id(
                managed_account_transfer_id=ma_transfer.id
            )
        )

    async def test_managed_account_balance_check_store_positive_amount_with_ma_transfer_not_need_more_balance(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # given store account and positive amount to create transfer, if ma_transfer exists and amount still needed <= ma_transfer.amount, nothing will be created/updated
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, entity="store", account_id=sma.id
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert not ma_transfer.amount == 0
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=1000,
            stripe=stripe,
        )  # amount_still_needed = 980
        assert (
            ma_transfer
            == await managed_account_transfer_repo.get_managed_account_transfer_by_id(
                managed_account_transfer_id=ma_transfer.id
            )
        )

    async def test_managed_account_balance_check_dasher_positive_amount_without_ma_transfer(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        @asyncio.coroutine
        def mock_get_country_shortname(*args, **kwargs):
            return "US"

        mocker.patch(
            "app.payout.core.transfer.create_standard_payout.get_country_shortname",
            side_effect=mock_get_country_shortname,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=1000,
            stripe=stripe,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer.id
        )
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 1000
        assert retrieved_ma_transfer.transfer_id == transfer.id
        assert retrieved_ma_transfer.payment_account_id == payment_account.id

    async def test_managed_account_balance_check_store_positive_amount_without_ma_transfer(
        self,
        mocker: pytest_mock.MockFixture,
        payment_account_repo: PaymentAccountRepository,
        transfer_repo: TransferRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
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
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, entity="store", account_id=sma.id
        )
        await self.create_standard_payout_operation.managed_account_balance_check(
            payment_account=payment_account,
            transfer_id=transfer.id,
            amount=1000,
            stripe=stripe,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer.id
        )  # amount_still_needed = 980
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 980
        assert retrieved_ma_transfer.transfer_id == transfer.id
        assert retrieved_ma_transfer.payment_account_id == payment_account.id

    async def test_submit_managed_account_transfer_negative_amount(
        self,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        # when a managed_account_transfer with negative amount attempts to submit, nothing will happen
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
            amount=-100,
        )
        await self.create_standard_payout_operation.submit_managed_account_transfer(
            managed_account_transfer=ma_transfer,
            payment_account=payment_account,
            stripe=stripe,
        )
        assert (
            ma_transfer
            == await managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
                transfer_id=transfer.id
            )
        )

    async def test_submit_managed_account_transfer_positive_amount_success(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        stripe: StripeAsyncClient,
    ):
        mocked_transfer = mock_transfer()

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            return mocked_transfer

        mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo, account_id=sma.id
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        await self.create_standard_payout_operation.submit_managed_account_transfer(
            managed_account_transfer=ma_transfer,
            payment_account=payment_account,
            stripe=stripe,
        )
        retrieved_ma_transfer = await managed_account_transfer_repo.get_managed_account_transfer_by_id(
            managed_account_transfer_id=ma_transfer.id
        )
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.stripe_id == mocked_transfer.id
        assert (
            retrieved_ma_transfer.stripe_status
            == ManagedAccountTransferStatus.PAID.value
        )
        assert retrieved_ma_transfer.submitted_at

    async def test_get_stripe_transfer_metadata_payment_account_and_type_id(
        self, payment_account_repo: PaymentAccountRepository
    ):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repo
        )
        transfer_metadata = self.create_standard_payout_operation.get_stripe_transfer_metadata(
            transfer_id=1234,
            payment_account=payment_account,
            target_type=PayoutTargetType.DASHER,
            target_id="123",
        )
        assert len(transfer_metadata) == 4
        assert transfer_metadata["transfer_id"] == 1234
        assert transfer_metadata["account_id"] == payment_account.id
        assert transfer_metadata["target_type"] == PayoutTargetType.DASHER
        assert transfer_metadata["target_id"] == 123
