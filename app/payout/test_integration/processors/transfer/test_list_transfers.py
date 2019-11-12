import pytest
import pytest_mock

from app.commons.database.infra import DB
from app.payout.core.transfer.processors.list_transfers import (
    ListTransfers,
    ListTransfersRequest,
)
from app.payout.repository.maindb.payment_account import PaymentAccountRepository
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import (
    prepare_and_insert_transfer,
    prepare_and_insert_payment_account,
)


class TestListTransfers:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        transfer_repo: TransferRepository,
        payment_account_repo: PaymentAccountRepository,
    ):
        self.transfer_repo = transfer_repo
        self.payment_account_repo = payment_account_repo
        self.mocker = mocker

    @pytest.fixture
    def transfer_repo(self, payout_maindb: DB) -> TransferRepository:
        return TransferRepository(database=payout_maindb)

    @pytest.fixture
    def payment_account_repo(self, payout_maindb: DB) -> PaymentAccountRepository:
        return PaymentAccountRepository(database=payout_maindb)

    def _construct_list_transfers_op(self, payment_account_ids=None):
        return ListTransfers(
            transfer_repo=self.transfer_repo,
            logger=self.mocker.Mock(),
            request=ListTransfersRequest(
                payment_account_ids=payment_account_ids, offset=0, limit=50
            ),
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
