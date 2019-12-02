from datetime import datetime, timedelta, timezone

import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.database.infra import DB
from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.core.transfer.processors.list_transfers import (
    ListTransfers,
    ListTransfersRequest,
)
from app.payout.models import TimeRange
from app.payout.repository.maindb.model.transfer import TransferStatus
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.stripe_transfer import StripeTransferRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_payment_account,
    prepare_and_insert_stripe_transfer,
)


class TestListTransfers:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
        stripe_transfer_repo: StripeTransferRepository,
    ):
        self.transfer_repo = transfer_repo
        self.payment_account_repo = payment_account_repo
        self.stripe_transfer_repo = stripe_transfer_repo
        self.mocker = mocker

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    @pytest.fixture
    def stripe_transfer_repo(self, payout_maindb: DB) -> StripeTransferRepository:
        return StripeTransferRepository(database=payout_maindb)

    def _construct_list_transfers_op(
        self,
        has_positive_amount=None,
        time_range=None,
        is_submitted=None,
        status=None,
        payment_account_ids=None,
        offset=0,
        limit=50,
    ):
        return ListTransfers(
            transfer_repo=self.transfer_repo,
            logger=self.mocker.Mock(),
            request=ListTransfersRequest(
                payment_account_ids=payment_account_ids,
                has_positive_amount=has_positive_amount,
                time_range=time_range,
                is_submitted=is_submitted,
                status=status,
                offset=offset,
                limit=limit,
            ),
        )

    async def test_execute_list_transfers_with_payment_account_ids_invalid_input(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        with pytest.raises(PayoutError) as e:
            await self._construct_list_transfers_op(
                payment_account_ids=[payment_account.id], offset=-1
            )._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.INVALID_INPUT
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.INVALID_INPUT.value]
        )

    async def test_execute_list_transfers_with_payment_account_ids_unsupported_use_cases(
        self
    ):
        with pytest.raises(PayoutError) as e:
            await self._construct_list_transfers_op()._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.UNSUPPORTED_USECASE
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.UNSUPPORTED_USECASE.value]
        )

    async def test_execute_list_transfers_with_payment_account_ids_not_found(self):
        payment_account = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        response = await self._construct_list_transfers_op(
            payment_account_ids=[payment_account.id]
        )._execute()
        assert not response.transfers
        assert response.count == 0

    async def test_execute_list_transfers_with_payment_account_ids_success(self):
        payment_account_a = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )
        payment_account_b = await prepare_and_insert_payment_account(
            payment_account_repo=self.payment_account_repo
        )

        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account_a.id
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account_a.id
        )
        transfer_c = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, payment_account_id=payment_account_b.id
        )
        response = await self._construct_list_transfers_op(
            payment_account_ids=[payment_account_a.id]
        )._execute()
        assert transfer_a in response.transfers
        assert transfer_b in response.transfers
        assert transfer_c not in response.transfers
        assert response.count == 2

    async def test_execute_list_positive_amount_transfers_with_status_and_time_range_success(
        self
    ):
        # test negative amount transfer/ wrong time_range and wrong status transfer and will not be listed out
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        original_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            has_positive_amount=True,
            status=TransferStatus.PENDING,
        )._execute()

        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.FAILED
        )

        end_time = datetime.now(timezone.utc)
        new_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            has_positive_amount=True,
            status=TransferStatus.PENDING,
        )._execute()

        assert new_response.count - original_response.count == 1
        assert transfer_a in new_response.transfers
        assert transfer_a not in original_response.transfers
        assert transfer_b not in new_response.transfers
        assert transfer_b not in original_response.transfers
        assert transfer_c not in new_response.transfers
        assert transfer_c not in original_response.transfers

        transfer_d = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING
        )
        response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            has_positive_amount=True,
            status=TransferStatus.PENDING,
        )._execute()
        assert transfer_d not in response.transfers

    async def test_execute_list_transfers_with_status_and_time_range_success(self):
        # test wrong time_range and wrong status transfer and will not be listed out, negative amount transfer will be listed
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        original_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            status=TransferStatus.PENDING,
        )._execute()

        transfer_a = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING
        )
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.FAILED
        )

        end_time = datetime.now(timezone.utc)
        new_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            status=TransferStatus.PENDING,
        )._execute()

        assert new_response.count - original_response.count == 2
        assert transfer_a in new_response.transfers
        assert transfer_a not in original_response.transfers
        assert transfer_b in new_response.transfers
        assert transfer_b not in original_response.transfers
        assert transfer_c not in new_response.transfers
        assert transfer_c not in original_response.transfers

        transfer_d = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING
        )
        response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            status=TransferStatus.PENDING,
        )._execute()
        assert transfer_d not in response.transfers

    async def test_execute_list_positive_amount_transfers_with_stripe_transfer(self):
        # test negative amount transfer/ wrong time_range transfer and will not be listed out
        # test with is_submitted flag off
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        original_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            is_submitted=False,
            has_positive_amount=True,
        )._execute()
        transfer_a = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer_c.id
        )
        end_time = datetime.now(timezone.utc)
        new_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            is_submitted=False,
            has_positive_amount=True,
        )._execute()

        assert new_response.count - original_response.count == 2
        assert transfer_a in new_response.transfers
        assert transfer_a not in original_response.transfers
        assert transfer_b not in new_response.transfers
        assert transfer_b not in original_response.transfers
        assert transfer_c in new_response.transfers
        assert transfer_c not in original_response.transfers

        transfer_d = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING
        )
        response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            is_submitted=False,
            has_positive_amount=True,
        )._execute()
        assert transfer_d not in response.transfers

    async def test_execute_list_positive_amount_transfers_without_stripe_transfer(self):
        # test negative amount transfer/ wrong time_range transfer and will not be listed out
        # test with is_submitted flag on
        start_time = datetime.now(timezone.utc) - timedelta(days=1)
        end_time = datetime.now(timezone.utc)
        original_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            is_submitted=True,
            has_positive_amount=True,
        )._execute()
        transfer_a = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        transfer_b = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, amount=-1
        )
        transfer_c = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        await prepare_and_insert_stripe_transfer(
            stripe_transfer_repo=self.stripe_transfer_repo, transfer_id=transfer_c.id
        )
        end_time = datetime.now(timezone.utc)
        new_response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            is_submitted=True,
            has_positive_amount=True,
        )._execute()

        assert new_response.count - original_response.count == 1
        assert transfer_a not in new_response.transfers
        assert transfer_a not in original_response.transfers
        assert transfer_b not in new_response.transfers
        assert transfer_b not in original_response.transfers
        assert transfer_c in new_response.transfers
        assert transfer_c not in original_response.transfers

        transfer_d = await prepare_and_insert_transfer(
            transfer_repo=self.transfer_repo, status=TransferStatus.PENDING
        )
        response = await self._construct_list_transfers_op(
            time_range=TimeRange(start_time=start_time, end_time=end_time),
            is_submitted=False,
            has_positive_amount=True,
        )._execute()
        assert transfer_d not in response.transfers
