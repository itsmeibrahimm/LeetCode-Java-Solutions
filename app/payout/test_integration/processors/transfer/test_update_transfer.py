import pytest
import pytest_mock
from starlette.status import HTTP_400_BAD_REQUEST

from app.payout.core.exceptions import (
    PayoutError,
    PayoutErrorCode,
    payout_error_message_maps,
)
from app.payout.core.transfer.processors.update_transfer import (
    UpdateTransfer,
    UpdateTransferRequest,
)
from app.payout.repository.maindb.model.transfer import TransferStatus
from app.payout.repository.maindb.transfer import TransferRepository
from app.payout.test_integration.utils import prepare_and_insert_transfer


class TestUpdateTransfer:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self, mocker: pytest_mock.MockFixture, transfer_repo: TransferRepository):
        self.transfer_repo = transfer_repo
        self.mocker = mocker

    def _construct_update_transfer_op(self, transfer_id: int):
        return UpdateTransfer(
            transfer_repo=self.transfer_repo,
            logger=self.mocker.Mock(),
            request=UpdateTransferRequest(
                transfer_id=transfer_id, status=TransferStatus.PENDING
            ),
        )

    async def test_execute_update_transfer_not_found(self):
        with pytest.raises(PayoutError) as e:
            await self._construct_update_transfer_op(transfer_id=-1)._execute()
        assert e.value.status_code == HTTP_400_BAD_REQUEST
        assert e.value.error_code == PayoutErrorCode.TRANSFER_NOT_FOUND
        assert (
            e.value.error_message
            == payout_error_message_maps[PayoutErrorCode.TRANSFER_NOT_FOUND.value]
        )

    async def test_execute_get_transfer_by_id_success(self):
        transfer = await prepare_and_insert_transfer(transfer_repo=self.transfer_repo)
        response = await self._construct_update_transfer_op(
            transfer_id=transfer.id
        )._execute()
        assert transfer.id == response.transfer.id
        assert response.transfer.status == TransferStatus.PENDING
