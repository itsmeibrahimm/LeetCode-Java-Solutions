import uuid

import pytest
import pytest_mock
from psycopg2._psycopg import DataError

from app.commons.types import CurrencyType
from app.ledger.core.data_types import InsertMxLedgerInput, GetMxLedgerByIdInput
from app.ledger.core.exceptions import (
    MxLedgerProcessError,
    LedgerErrorCode,
    ledger_error_message_maps,
)
from app.ledger.core.mx_ledger.processor import MxLedgerProcessor
from app.ledger.core.types import MxLedgerType, MxLedgerStateType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository


class TestMxLedgerProcessor:
    pytestmark = [pytest.mark.asyncio]

    async def test_process_mx_ledger_success(
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

        mx_ledger = await mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)
        assert mx_ledger.id == mx_ledger_id
        assert mx_ledger.state == MxLedgerStateType.PROCESSING

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
            "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.process_mx_ledger_state",
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
