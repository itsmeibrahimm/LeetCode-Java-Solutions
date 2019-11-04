import uuid
from uuid import UUID
from datetime import datetime

import pytest
import pytest_mock
from asynctest import patch

from app.commons.core.errors import DBDataError, DBOperationLockNotAvailableError
from app.commons.database.infra import DB
from app.ledger.core.data_types import GetMxLedgerByIdInput
from app.ledger.core.exceptions import (
    MxLedgerProcessError,
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
)
from app.ledger.core.mx_ledger.processors.process_mx_ledger import (
    ProcessMxLedger,
    ProcessMxLedgerRequest,
)
from app.ledger.core.types import MxLedgerStateType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.test_integration.utils import (
    prepare_mx_ledger,
    prepare_mx_scheduled_ledger,
)


class TestProcessMxLedger:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self, mocker: pytest_mock.MockFixture, mx_ledger_repository: MxLedgerRepository
    ):
        self.mx_ledger_repository = mx_ledger_repository
        self.mocker = mocker

    def _construct_process_ledger_request(self, mx_ledger_id: UUID):
        request = ProcessMxLedger(
            mx_ledger_repo=self.mx_ledger_repository,
            logger=self.mocker.Mock(),
            request=ProcessMxLedgerRequest(mx_ledger_id=mx_ledger_id),
        )
        return request

    @pytest.fixture
    def mx_scheduled_ledger_repo(
        self, ledger_paymentdb: DB
    ) -> MxScheduledLedgerRepository:
        return MxScheduledLedgerRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_ledger_repository(self, ledger_paymentdb: DB) -> MxLedgerRepository:
        return MxLedgerRepository(database=ledger_paymentdb)

    async def test_process_mx_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repo: MxScheduledLedgerRepository,
    ):
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        mx_scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=mx_ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repo.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )
        create_mx_ledger_op = self._construct_process_ledger_request(
            mx_ledger_id=mx_ledger_id
        )

        mx_ledger = await create_mx_ledger_op._execute()
        assert mx_ledger.id == mx_ledger_id
        assert mx_ledger.state == MxLedgerStateType.PROCESSING

    async def test_process_mx_ledger_not_found_raise_exception(self):
        create_mx_ledger_op = self._construct_process_ledger_request(
            mx_ledger_id=uuid.uuid4()
        )
        with pytest.raises(MxLedgerReadError) as e:
            await create_mx_ledger_op._execute()

        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_NOT_FOUND
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_NOT_FOUND.value]
        )

    async def test_process_mx_ledger_invalid_state_raise_exception(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        create_mx_ledger_op = self._construct_process_ledger_request(
            mx_ledger_id=mx_ledger_id
        )
        with pytest.raises(MxLedgerInvalidProcessStateError) as e:
            await create_mx_ledger_op._execute()

        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE
        assert (
            e.value.error_message
            == ledger_error_message_maps[
                LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
            ]
        )

    async def test_process_mx_ledger_data_error_raise_exception(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        error = DBDataError("Test data error.")
        self.mocker.patch(
            "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.move_ledger_state_to_processing_and_close_schedule_ledger",
            side_effect=error,
        )
        create_mx_ledger_op = self._construct_process_ledger_request(
            mx_ledger_id=mx_ledger_id
        )
        with pytest.raises(MxLedgerProcessError) as e:
            await create_mx_ledger_op._execute()

        get_ledger_request = GetMxLedgerByIdInput(id=mx_ledger_id)
        mx_ledger_retrieved = await mx_ledger_repository.get_ledger_by_id(
            get_ledger_request
        )
        assert mx_ledger_retrieved is not None
        assert mx_ledger_retrieved.id == mx_ledger_id
        assert mx_ledger_retrieved.state == MxLedgerStateType.OPEN
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_PROCESS_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_PROCESS_ERROR.value]
        )

    @patch(
        "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.move_ledger_state_to_processing_and_close_schedule_ledger"
    )
    async def test_process_mx_ledger_retry_exceed_attempt_raise_exception(
        self, mock_process_ledger, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        error = DBOperationLockNotAvailableError()
        mock_process_ledger.side_effect = error
        process_mx_ledger_op = self._construct_process_ledger_request(
            mx_ledger_id=ledger_id
        )
        with pytest.raises(MxLedgerProcessError) as e:
            await process_mx_ledger_op._execute()

        assert (
            e.value.error_code
            == LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR
        )
        assert (
            e.value.error_message
            == ledger_error_message_maps[
                LedgerErrorCode.MX_LEDGER_UPDATE_LOCK_NOT_AVAILABLE_ERROR.value
            ]
        )
