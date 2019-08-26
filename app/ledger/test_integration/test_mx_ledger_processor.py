import uuid
from datetime import datetime

import pytest
import pytest_mock
from psycopg2._psycopg import DataError

from app.commons.types import CurrencyType
from app.ledger.core.data_types import (
    InsertMxLedgerInput,
    GetMxLedgerByIdInput,
    InsertMxScheduledLedgerInput,
)
from app.ledger.core.exceptions import (
    MxLedgerProcessError,
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
)
from app.ledger.core.mx_ledger.processor import MxLedgerProcessor
from app.ledger.core.types import (
    MxLedgerType,
    MxLedgerStateType,
    MxScheduledLedgerIntervalType,
)
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)


class TestMxLedgerProcessor:
    pytestmark = [pytest.mark.asyncio]

    async def test_process_mx_ledger_success(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_processor = MxLedgerProcessor(
            mx_ledger_repo=mx_ledger_repository, log=mocker.Mock()
        )
        mx_ledger_to_insert = InsertMxLedgerInput(
            id=mx_ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        mx_scheduled_ledger_id = uuid.uuid4()
        mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
            id=mx_scheduled_ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=mx_ledger_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
            closed_at=0,
            start_time=datetime(2019, 7, 29, 7),
            end_time=datetime(2019, 8, 5, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        mx_ledger = await mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)
        assert mx_ledger.id == mx_ledger_id
        assert mx_ledger.state == MxLedgerStateType.PROCESSING

    async def test_process_mx_ledger_not_found_raise_exception(
        self, mocker: pytest_mock.MockFixture, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_processor = MxLedgerProcessor(
            mx_ledger_repo=mx_ledger_repository, log=mocker.Mock()
        )
        with pytest.raises(MxLedgerReadError) as e:
            await mx_ledger_processor.process(mx_ledger_id=uuid.uuid4())

        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_NOT_FOUND
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_NOT_FOUND.value]
        )

    async def test_process_mx_ledger_invalid_state_raise_exception(
        self, mocker: pytest_mock.MockFixture, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_id = uuid.uuid4()
        mx_ledger_processor = MxLedgerProcessor(
            mx_ledger_repo=mx_ledger_repository, log=mocker.Mock()
        )
        mx_ledger_to_insert = InsertMxLedgerInput(
            id=mx_ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.PROCESSING.value,
            balance=2000,
            payment_account_id="pay_act_test_id",
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)
        with pytest.raises(MxLedgerInvalidProcessStateError) as e:
            await mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)

        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE
        assert (
            e.value.error_message
            == ledger_error_message_maps[
                LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
            ]
        )

    async def test_process_mx_ledger_data_error_raise_exception(
        self, mocker: pytest_mock.MockFixture, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_id = uuid.uuid4()
        mx_ledger_processor = MxLedgerProcessor(
            mx_ledger_repo=mx_ledger_repository, log=mocker.Mock()
        )
        mx_ledger_to_insert = InsertMxLedgerInput(
            id=mx_ledger_id,
            type=MxLedgerType.MANUAL.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id="pay_act_test_id",
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)
        error = DataError("Test data error.")
        mocker.patch(
            "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.process_mx_ledger_state_and_close_schedule_ledger",
            side_effect=error,
        )
        with pytest.raises(MxLedgerProcessError) as e:
            await mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)

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
