import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.core.transfer.processors.submit_transfer import (
    SubmitTransfer,
    SubmitTransferRequest,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepository
from app.payout.repository.maindb.managed_account_transfer import (
    ManagedAccountTransferRepository,
)
from app.payout.repository.maindb.model.transfer import TransferStatus
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_payment_account,
    prepare_and_insert_managed_account_transfer,
    prepare_and_insert_transfer,
    prepare_and_insert_stripe_managed_account,
    mock_balance,
    prepare_and_insert_stripe_transfer,
    mock_payout,
    construct_stripe_error,
    prepare_and_insert_transaction,
    mock_transfer,
)
from app.payout.models import (
    PayoutTargetType,
    TransferStatusCodeType,
    StripeTransferSubmissionStatus,
    StripeErrorCode,
    STRIPE_TRANSFER_FAILED_STATUS,
    TransferMethodType,
)


class TestSubmitTransfer:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
        payment_account_repo: PaymentAccountRepository,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        transfer_repo: TransferRepository,
        transaction_repo: TransactionRepository,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepository,
        stripe_async_client: StripeAsyncClient,
    ):
        self.submit_transfer_operation = SubmitTransfer(
            transfer_repo=transfer_repo,
            stripe_transfer_repo=stripe_transfer_repo,
            payment_account_repo=payment_account_repo,
            managed_account_transfer_repo=managed_account_transfer_repo,
            transaction_repo=transaction_repo,
            payment_account_edit_history_repo=payment_account_edit_history_repo,
            logger=mocker.Mock(),
            stripe=stripe_async_client,
            request=SubmitTransferRequest(transfer_id="1234"),
        )
        self.transfer_repo = transfer_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.payment_account_repo = payment_account_repo
        self.managed_account_transfer_repo = managed_account_transfer_repo
        self.transaction_repo = transaction_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.mocker = mocker
        self.stripe = stripe_async_client

    def _construct_submit_transfer_op(self, transfer_id: int, retry=False, method=None):
        return SubmitTransfer(
            transfer_repo=self.transfer_repo,
            stripe_transfer_repo=self.stripe_transfer_repo,
            payment_account_repo=self.payment_account_repo,
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            transaction_repo=self.transaction_repo,
            payment_account_edit_history_repo=self.payment_account_edit_history_repo,
            logger=self.mocker.Mock(),
            stripe=self.stripe,
            request=SubmitTransferRequest(
                transfer_id=transfer_id,
                statement_descriptor="statement_descriptor",
                retry=retry,
                method=method,
            ),
        )

    async def test_execute_submit_transfer_invalid_payment_account(self):
        # prepare and insert transfer with invalid payment account
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=-1
        )
        submit_transfer_op = self._construct_submit_transfer_op(transfer_id=transfer.id)
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_PAYMENT_ACCOUNT_ID.value
            ]
        )

    async def test_execute_submit_transfer_no_transaction_found(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        submit_transfer_op = self._construct_submit_transfer_op(transfer_id=transfer.id)
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_INVALID_STATE
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.TRANSFER_INVALID_STATE.value]
        )
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.ERROR
        assert (
            retrieved_transfer.status_code == TransferStatusCodeType.ERROR_INVALID_STATE
        )

    async def test_execute_submit_transfer_amount_not_match(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )

        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )

        submit_transfer_op = self._construct_submit_transfer_op(transfer_id=transfer.id)
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.MISMATCHED_TRANSFER_AMOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.MISMATCHED_TRANSFER_AMOUNT.value
            ]
        )
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.ERROR
        assert (
            retrieved_transfer.status_code
            == TransferStatusCodeType.ERROR_AMOUNT_MISMATCH
        )

    async def test_execute_submit_transfer_not_retry_and_transfer_submitted(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=1000,
            submitted_at=datetime.now(timezone.utc),
        )

        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )

        submit_transfer_op = self._construct_submit_transfer_op(transfer_id=transfer.id)
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.DUPLICATE_TRANSFER
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.DUPLICATE_TRANSFER.value]
        )

    async def test_execute_submit_transfer_not_retry_and_has_transfer_submission(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=1000,
        )
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )

        submit_transfer_op = self._construct_submit_transfer_op(transfer_id=transfer.id)
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.DUPLICATE_TRANSFER
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.DUPLICATE_TRANSFER.value]
        )

    async def test_execute_submit_transfer_retry_but_transfer_disabled(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, transfers_enabled=False
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=1000,
            status=TransferStatus.ERROR,
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )

        submit_transfer_op = self._construct_submit_transfer_op(
            transfer_id=transfer.id, retry=True
        )
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_DISABLED_ERROR
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.TRANSFER_DISABLED_ERROR.value]
        )

    async def test_execute_submit_transfer_zero_amount_dummy_transfer(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=0,
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
            amount=0,
        )

        submit_transfer_op = self._construct_submit_transfer_op(
            transfer_id=transfer.id, method=TransferMethodType.STRIPE
        )
        assert await submit_transfer_op._execute()
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.PAID
        assert retrieved_transfer.submitted_at
        assert not retrieved_transfer.status_code

    async def test_execute_submit_transfer_with_dummy_transfer_method(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=1000,
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )

        submit_transfer_op = self._construct_submit_transfer_op(
            transfer_id=transfer.id, method=TransferMethodType.COD_INVOICE
        )
        assert await submit_transfer_op._execute()
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.PAID
        assert retrieved_transfer.submitted_at
        assert not retrieved_transfer.status_code

    async def test_execute_submit_transfer_transfer_processing(self):
        # prepare and insert transfer and payment account without account_id
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=1000,
        )
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            payout_account_id=payment_account.id,
            transfer_id=transfer.id,
        )

        submit_transfer_op = self._construct_submit_transfer_op(
            transfer_id=transfer.id, retry=True, method=TransferMethodType.STRIPE
        )
        with pytest.raises(PayoutError) as e:
            await submit_transfer_op._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_PROCESSING
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.TRANSFER_PROCESSING.value]
        )

    async def test_execute_submit_transfer_success(self):
        # mocked get_json for runtime 'payment_account_transfer_limit_overrides'
        # mocked get_int for runtime 'default_transfer_max' and DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK
        # mocked get_bool for runtime 'FF_CHECK_FOR_RECENT_BANK_CHANGE'
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value={})
        self.mocker.patch("app.commons.runtime.runtime.get_int", side_effect=[{}, 14])
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        mocked_transfer = mock_transfer()

        @asyncio.coroutine
        def mock_create_transfer(*args, **kwargs):
            return mocked_transfer

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_transfer",
            side_effect=mock_create_transfer,
        )

        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_create_payout(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.create_payout",
            side_effect=mock_create_payout,
        )

        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )

        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=1000,
        )
        await prepare_and_insert_transaction(
            transaction_repo=self.transaction_repo,
            transfer_id=transfer.id,
            payout_account_id=payment_account.id,
        )
        submit_transfer_op = self._construct_submit_transfer_op(
            transfer_id=transfer.id, retry=True, method=TransferMethodType.STRIPE
        )
        assert await submit_transfer_op._execute()
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.PENDING
        assert retrieved_transfer.submitted_at
        assert not retrieved_transfer.status_code

    async def test_handle_dummy_transfer_success(self):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=12345
        )
        assert await self.submit_transfer_operation.handle_dummy_transfer(
            transfer_id=transfer.id, method="stripe"
        )

        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.method == "stripe"
        assert retrieved_transfer.status == TransferStatus.PAID
        assert not retrieved_transfer.status_code

    async def test_get_latest_transfer_submission_success(self):
        # prepare and insert transfer and stripe_transfer
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=12345
        )
        first_stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        second_stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )
        retrieved_stripe_transfer = await self.submit_transfer_operation.get_latest_transfer_submission(
            transfer_id=transfer.id, method="stripe"
        )
        assert not retrieved_stripe_transfer == first_stripe_transfer
        assert retrieved_stripe_transfer == second_stripe_transfer

    async def test_get_latest_transfer_submission_invalid_method(self):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=12345
        )
        assert not await self.submit_transfer_operation.get_latest_transfer_submission(
            transfer_id=transfer.id, method="invalid_method"
        )

    async def test_get_latest_transfer_submission_transfer_non_exist(self):
        assert not await self.submit_transfer_operation.get_latest_transfer_submission(
            transfer_id=-1, method="stripe"
        )

    async def test_transfer_amount_check_success(self):
        # mocked get_json for runtime 'payment_account_transfer_limit_overrides'
        # mocked get_int for runtime 'default_transfer_max' and DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK
        # mocked get_bool for runtime 'FF_CHECK_FOR_RECENT_BANK_CHANGE'
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value={})
        self.mocker.patch("app.commons.runtime.runtime.get_int", side_effect=[{}, 14])
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        await self.submit_transfer_operation.transfer_amount_check(
            transfer=transfer, submitted_by=None
        )

    async def test_transfer_amount_check_negative_transfer_amount(self):
        # mocked get_json for runtime 'payment_account_transfer_limit_overrides'
        # mocked get_int for runtime 'default_transfer_max' and DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK
        # mocked get_bool for runtime 'FF_CHECK_FOR_RECENT_BANK_CHANGE'
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value={})
        self.mocker.patch("app.commons.runtime.runtime.get_int", side_effect=[{}, 14])
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=-10,
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.transfer_amount_check(
                transfer=transfer, submitted_by=None
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_AMOUNT_NEGATIVE
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.TRANSFER_AMOUNT_NEGATIVE.value]
        )

        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.ERROR
        assert (
            retrieved_transfer.status_code
            == TransferStatusCodeType.ERROR_AMOUNT_LIMIT_EXCEEDED
        )

    async def test_transfer_amount_check_no_permission(self):
        # mocked get_json for runtime 'payment_account_transfer_limit_overrides'
        # mocked get_int for runtime 'default_transfer_max' and DAYS_FOR_RECENT_BANK_CHANGE_FOR_LARGE_TRANSFERS_CHECK
        # mocked get_bool for runtime 'FF_CHECK_FOR_RECENT_BANK_CHANGE'
        self.mocker.patch("app.commons.runtime.runtime.get_json", return_value={})
        self.mocker.patch("app.commons.runtime.runtime.get_int", side_effect=[{}, 14])
        self.mocker.patch("app.commons.runtime.runtime.get_bool", return_value=True)
        self.mocker.patch("app.commons.runtime.runtime.get_str", return_value="123")

        @asyncio.coroutine
        def mock_get_bank_update(*args, **kwargs):
            return {"id": 1}

        self.mocker.patch(
            "app.payout.repository.bankdb.payment_account_edit_history.PaymentAccountEditHistoryRepository.get_most_recent_bank_update",
            side_effect=mock_get_bank_update,
        )

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo,
            payment_account_id=payment_account.id,
            amount=3000000,
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.transfer_amount_check(
                transfer=transfer, submitted_by=None
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_AMOUNT_OVER_LIMIT
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.TRANSFER_AMOUNT_OVER_LIMIT.value
            ]
        )
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.ERROR
        assert (
            retrieved_transfer.status_code
            == TransferStatusCodeType.ERROR_AMOUNT_LIMIT_EXCEEDED
        )

    async def test_is_processing_or_processed_for_stripe_found_transfers(self):
        # prepare and insert transfer and stripe_transfer
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=12345
        )
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer.id
        )

        assert await self.submit_transfer_operation.is_processing_or_processed_for_method(
            transfer_id=transfer.id, method="stripe"
        )

    async def test_is_processing_or_processed_for_stripe_transfers_invalid_method(self):
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=12345
        )
        assert not await self.submit_transfer_operation.is_processing_or_processed_for_method(
            transfer_id=transfer.id, method="invalid_method"
        )

    async def test_is_processing_or_processed_for_stripe_transfers_not_exist(self):
        assert not await self.submit_transfer_operation.is_processing_or_processed_for_method(
            transfer_id=-1, method="stripe"
        )

    async def test_has_stripe_managed_account_success(self):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        assert await self.submit_transfer_operation.has_stripe_managed_account(
            payment_account=payment_account, transfer_id=transfer.id
        )

    async def test_has_stripe_managed_account_payment_account_without_account_id(self):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=None
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.has_stripe_managed_account(
                payment_account=payment_account, transfer_id=transfer.id
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )
        # make sure that transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.FAILED
        assert (
            retrieved_transfer.status_code
            == TransferStatusCodeType.ERROR_NO_GATEWAY_ACCOUNT
        )

    async def test_has_stripe_managed_account_no_sma(self):
        @asyncio.coroutine
        def mock_get_sma(*args):
            return None

        self.mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_stripe_managed_account_by_id",
            side_effect=mock_get_sma,
        )

        # prepare and insert payment_account and transfer
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.has_stripe_managed_account(
                payment_account=payment_account, transfer_id=transfer.id
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )
        # make sure that transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.FAILED
        assert (
            retrieved_transfer.status_code
            == TransferStatusCodeType.ERROR_NO_GATEWAY_ACCOUNT
        )

    async def test_get_stripe_account_id_success(self):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        stripe_id = await self.submit_transfer_operation.get_stripe_account_id(
            payment_account=payment_account
        )
        assert stripe_id

    async def test_get_stripe_account_id_no_account_id(self):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=None
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.get_stripe_account_id(
                payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_ACCOUNT.value]
        )

    async def test_get_stripe_account_id_no_sma(self):
        @asyncio.coroutine
        def mock_get_sma(*args):
            return None

        self.mocker.patch(
            "app.payout.repository.maindb.payment_account.PaymentAccountRepository.get_stripe_managed_account_by_id",
            side_effect=mock_get_sma,
        )

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.get_stripe_account_id(
                payment_account=payment_account
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_STRIPE_ACCOUNT.value]
        )

    async def test_managed_account_balance_check_store_positive_amount_without_ma_transfer(
        self
    ):

        mocked_balance = mock_balance()  # amount = 20

        @asyncio.coroutine
        def mock_retrieve_balance(*args, **kwargs):
            return mocked_balance

        self.mocker.patch(
            "app.commons.providers.stripe.stripe_client.StripeAsyncClient.retrieve_balance",
            side_effect=mock_retrieve_balance,
        )

        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo,
            entity="store",
            account_id=sma.id,
        )
        await self.submit_transfer_operation.managed_account_balance_check(
            payment_account=payment_account, transfer_id=transfer.id, amount=1000
        )
        retrieved_ma_transfer = await self.managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
            transfer_id=transfer.id
        )  # amount_still_needed = 980
        assert retrieved_ma_transfer
        assert retrieved_ma_transfer.amount == 980
        assert retrieved_ma_transfer.transfer_id == transfer.id
        assert retrieved_ma_transfer.payment_account_id == payment_account.id

    async def test_validate_payment_account_of_managed_account_transfer_success(self):

        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert await self.submit_transfer_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account,
            managed_account_transfer=ma_transfer,
            transfer_id=transfer.id,
        )

    async def test_validate_payment_account_of_managed_account_transfer_no_managed_account_transfer(
        self
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        assert await self.submit_transfer_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account,
            managed_account_transfer=None,
            transfer_id=transfer.id,
        )

    async def test_submit_stripe_transfer_success(self):
        # mocked out create_for_managed_account
        mocked_payout = mock_payout()

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            return mocked_payout

        self.mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        await self.submit_transfer_operation.submit_stripe_transfer(
            transfer_id=transfer.id,
            payment_account=payment_account,
            amount=100,
            submitted_by=123456,
            method=TransferMethodType.STRIPE,
        )
        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
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
        # check transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.submitted_at
        assert retrieved_transfer.submitted_by_id == 123456

    async def test_submit_stripe_transfer_handle_check_transfer(self):
        self.mocker.patch("app.commons.runtime.runtime.get_str", return_value="123")
        # prepare and insert payment_account and transfer
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                submitted_by=123456,
                method=TransferMethodType.CHECK,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_PERMISSION_ERROR
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.TRANSFER_PERMISSION_ERROR.value
            ]
        )

    async def test_submit_stripe_transfer_with_stripe_id_raise_exception(self):
        # prepare and insert payment_account and transfer
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )

        # mock out create_stripe_transfer with a non-empty stripe_id so _submit_stripe_transfer will raise exception
        mock_stripe_transfer = await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo,
            transfer_id=transfer.id,
            stripe_id=str(uuid.uuid4()),
        )

        @asyncio.coroutine
        def mock_create_stripe_transfer(*args, **kwargs):
            return mock_stripe_transfer

        self.mocker.patch(
            "app.payout.repository.maindb.stripe_transfer.StripeTransferRepository.create_stripe_transfer",
            side_effect=mock_create_stripe_transfer,
        )

        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                submitted_by=123456,
                method=TransferMethodType.STRIPE,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.DUPLICATE_STRIPE_TRANSFER
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.DUPLICATE_STRIPE_TRANSFER.value
            ]
        )

    async def test_submit_stripe_transfer_no_external_account_in_currency(self):
        error = construct_stripe_error(code=StripeErrorCode.NO_EXT_ACCOUNT_IN_CURRENCY)

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        self.mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                submitted_by=123456,
                method=TransferMethodType.STRIPE,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_PAYOUT_ACCT_MISSING
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
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

    async def test_submit_stripe_transfer_payout_not_allowed(self):
        error = construct_stripe_error(code=StripeErrorCode.PAYOUT_NOT_ALLOWED)

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        self.mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )

        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                submitted_by=123456,
                method=TransferMethodType.STRIPE,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_PAYOUT_DISALLOWED
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
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

    async def test_submit_stripe_transfer_invalid_request_error(self):
        error = construct_stripe_error(error_type=StripeErrorCode.INVALID_REQUEST_ERROR)

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        self.mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                submitted_by=123456,
                method=TransferMethodType.STRIPE,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_INVALID_REQUEST_ERROR
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
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

    async def test_submit_stripe_transfer_other_exception(self):
        error = construct_stripe_error(code="random_exception")

        @asyncio.coroutine
        def mock_create_for_managed_account(*args, **kwargs):
            raise error

        self.mocker.patch(
            "app.payout.core.transfer.processors.submit_transfer.SubmitTransfer.create_for_managed_account",
            side_effect=mock_create_for_managed_account,
        )

        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo, account_id=sma.id
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.submit_stripe_transfer(
                transfer_id=transfer.id,
                payment_account=payment_account,
                amount=100,
                submitted_by=123456,
                method=TransferMethodType.STRIPE,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.STRIPE_SUBMISSION_ERROR
        assert e.value.error_message == "error_msg"

        retrieved_stripe_transfer = await self.stripe_transfer_repo.get_latest_stripe_transfer_by_transfer_id(
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

    async def test_validate_payment_account_of_managed_account_transfer_id_not_equal(
        self
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account.id
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            payment_account_id=111,
            transfer_id=transfer.id,
        )
        with pytest.raises(PayoutError) as e:
            await self.submit_transfer_operation.validate_payment_account_of_managed_account_transfer(
                payment_account=payment_account,
                managed_account_transfer=ma_transfer,
                transfer_id=transfer.id,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.MISMATCHED_TRANSFER_PAYMENT_ACCOUNT
        assert (
            e.value.error_message
            == f"Transfer: {payment_account.id}; Managed Account Transfer: {ma_transfer.payment_account_id}"
        )

        # make sure that transfer is updated
        retrieved_transfer = await self.transfer_repo.get_transfer_by_id(
            transfer_id=transfer.id
        )
        assert retrieved_transfer
        assert retrieved_transfer.status == TransferStatus.ERROR
        assert (
            retrieved_transfer.status_code
            == TransferStatusCodeType.ERROR_ACCOUNT_ID_MISMATCH
        )

    async def test_submit_managed_account_transfer_negative_amount(self):
        # when a managed_account_transfer with negative amount attempts to submit, nothing will happen
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=self.managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
            amount=-100,
        )
        await self.submit_transfer_operation.submit_managed_account_transfer(
            managed_account_transfer=ma_transfer, payment_account=payment_account
        )
        assert (
            ma_transfer
            == await self.managed_account_transfer_repo.get_managed_account_transfer_by_transfer_id(
                transfer_id=transfer.id
            )
        )

    async def test_get_stripe_transfer_metadata_payment_account_and_type_id(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        transfer_metadata = self.submit_transfer_operation.get_stripe_transfer_metadata(
            transfer_id=1234,
            payment_account=payment_account,
            target_type=PayoutTargetType.DASHER,
            target_id=123,
        )
        assert len(transfer_metadata) == 4
        assert transfer_metadata["transfer_id"] == 1234
        assert transfer_metadata["account_id"] == payment_account.id
        assert transfer_metadata["target_type"] == PayoutTargetType.DASHER
        assert transfer_metadata["target_id"] == 123

    async def test_extract_failure_code_from_exception_message_success(self):
        msg = "Sorry, you don't have any external accounts in that currency (usd)"
        failure_msg = self.submit_transfer_operation.extract_failure_code_from_exception_message(
            message=msg
        )
        assert failure_msg == "no_external_account_in_currency"

    async def test_extract_failure_code_from_exception_message_no_msg(self):
        error_msg = self.submit_transfer_operation.extract_failure_code_from_exception_message(
            message=None
        )
        assert error_msg == "err"

    async def test_extract_failure_code_from_exception_message_msg_not_match(self):
        msg = "I am a piece of random message"
        error_msg = self.submit_transfer_operation.extract_failure_code_from_exception_message(
            message=msg
        )
        assert error_msg == "err"

    async def test_does_user_have_payments_superpowers_empty_user_list(self):
        is_admin = self.submit_transfer_operation.does_user_have_payments_superpowers(
            user_list=[], runtime_list_name="transfer_amount_limitation_admins"
        )
        assert not is_admin

    async def test_does_user_have_payments_superpowers_user_not_in_the_runtime_list(
        self
    ):
        self.mocker.patch(
            "app.commons.runtime.runtime.get_str", return_value="123, 234, 345"
        )
        is_admin = self.submit_transfer_operation.does_user_have_payments_superpowers(
            user_list=[987], runtime_list_name="transfer_amount_limitation_admins"
        )
        assert not is_admin

    async def test_does_user_have_payments_superpowers_user_in_the_runtime_list(self):
        self.mocker.patch(
            "app.commons.runtime.runtime.get_str", return_value="123, 234, 345"
        )
        is_admin = self.submit_transfer_operation.does_user_have_payments_superpowers(
            user_list=[123], runtime_list_name="transfer_amount_limitation_admins"
        )
        assert is_admin
