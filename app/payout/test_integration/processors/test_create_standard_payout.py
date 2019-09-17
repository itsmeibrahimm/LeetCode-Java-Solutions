import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.database.infra import DB
from app.payout.core.account.processors.create_standard_payout import (
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
)
from app.payout.types import PayoutType, AccountType


class TestCreateStandardPayoutUtils:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        self.payment_account_id = 1234567894
        self.create_standard_payout_operation = CreateStandardPayout(
            stripe_transfer_repo=stripe_transfer_repo,
            logger=mocker.Mock(),
            request=CreateStandardPayoutRequest(
                payout_account_id=self.payment_account_id,
                amount=200,
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
    def payment_account_repository(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def managed_account_transfer_repo(
        self, payout_maindb: DB
    ) -> ManagedAccountTransferRepository:
        return ManagedAccountTransferRepository(database=payout_maindb)

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
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repository
        )
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=sma.id
        )
        assert await self.create_standard_payout_operation.has_stripe_managed_account(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )

    async def test_has_stripe_managed_account_no_payment_account(
        self, payment_account_repository: PaymentAccountRepository
    ):
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.has_stripe_managed_account(
                payment_account=None,
                payment_account_repository=payment_account_repository,
            )
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID
        assert (
            e.value.error_message
            == payout_error_message_maps[
                PayoutErrorCode.INVALID_STRIPE_ACCOUNT_ID.value
            ]
        )

    async def test_has_stripe_managed_account_payment_account_without_account_id(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=None
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.has_stripe_managed_account(
                payment_account=payment_account,
                payment_account_repository=payment_account_repository,
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
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository
        )
        with pytest.raises(PayoutError) as e:
            await self.create_standard_payout_operation.has_stripe_managed_account(
                payment_account=payment_account,
                payment_account_repository=payment_account_repository,
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
        payment_account_repository: PaymentAccountRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository
        )
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=payment_account.id,
            transfer_id=transfer.id,
        )
        assert await self.create_standard_payout_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account, managed_account_transfer=ma_transfer
        )

    async def test_validate_payment_account_of_managed_account_transfer_no_payment_account(
        self,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repository: PaymentAccountRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        ma_transfer = await prepare_and_insert_managed_account_transfer(
            managed_account_transfer_repo=managed_account_transfer_repo,
            payment_account_id=-1,
            transfer_id=transfer.id,
        )
        assert await self.create_standard_payout_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=None, managed_account_transfer=ma_transfer
        )

    async def test_validate_payment_account_of_managed_account_transfer_no_managed_account_transfer(
        self,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repository: PaymentAccountRepository,
    ):
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository
        )
        assert await self.create_standard_payout_operation.validate_payment_account_of_managed_account_transfer(
            payment_account=payment_account, managed_account_transfer=None
        )

    async def test_validate_payment_account_of_managed_account_transfer_id_not_equal(
        self,
        managed_account_transfer_repo: ManagedAccountTransferRepository,
        payment_account_repository: PaymentAccountRepository,
        transfer_repo: TransferRepository,
    ):
        # prepare and insert transfer to get a random id
        transfer = await prepare_and_insert_transfer(transfer_repo=transfer_repo)
        # prepare and insert payment_account
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository
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

    async def test_get_stripe_account_id_and_payment_account_type_success(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert stripe_managed_account
        sma = await prepare_and_insert_stripe_managed_account(
            payment_account_repo=payment_account_repository
        )
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=sma.id
        )
        stripe_id, account_type = await self.create_standard_payout_operation.get_stripe_account_id_and_payment_account_type(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )
        assert stripe_id
        assert account_type == AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT

    async def test_get_stripe_account_id_and_payment_account_type_no_account_id(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository, account_id=None
        )
        stripe_id, account_type = await self.create_standard_payout_operation.get_stripe_account_id_and_payment_account_type(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )
        assert not stripe_id
        assert account_type == AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT

    async def test_get_stripe_account_id_and_payment_account_type_no_sma(
        self, payment_account_repository: PaymentAccountRepository
    ):
        # prepare and insert payment_account, update its account_id field as None
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=payment_account_repository
        )
        stripe_id, account_type = await self.create_standard_payout_operation.get_stripe_account_id_and_payment_account_type(
            payment_account=payment_account,
            payment_account_repository=payment_account_repository,
        )
        assert not stripe_id
        assert account_type == AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT

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
