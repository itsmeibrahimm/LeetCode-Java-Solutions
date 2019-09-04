import uuid
from datetime import datetime

import pytest
import pytest_mock
from asynctest import patch
from psycopg2._psycopg import DataError, OperationalError
from psycopg2.errorcodes import LOCK_NOT_AVAILABLE

from app.commons.database.client.interface import DBTransaction
from app.ledger.core.data_types import (
    GetMxLedgerByIdInput,
    GetMxScheduledLedgerByAccountInput,
)
from app.commons.types import CurrencyType
from app.ledger.core.data_types import GetMxLedgerByIdInput
from app.ledger.core.exceptions import (
    MxLedgerProcessError,
    LedgerErrorCode,
    ledger_error_message_maps,
    MxLedgerReadError,
    MxLedgerInvalidProcessStateError,
    MxLedgerSubmissionError,
    MxLedgerCreationError,
)
from app.ledger.core.mx_ledger.processor import MxLedgerProcessor
from app.ledger.core.types import MxLedgerType, MxLedgerStateType, MxTransactionType
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.ledger.test_integration.utils import (
    prepare_mx_ledger,
    prepare_mx_scheduled_ledger,
)


class TestMxLedgerProcessor:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        self.mx_ledger_processor = MxLedgerProcessor(
            mx_ledger_repo=mx_ledger_repository,
            mx_transaction_repo=mx_transaction_repository,
            log=mocker.Mock(),
        )

    async def test_process_mx_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
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
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        mx_ledger = await self.mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)
        assert mx_ledger.id == mx_ledger_id
        assert mx_ledger.state == MxLedgerStateType.PROCESSING

    async def test_process_mx_ledger_not_found_raise_exception(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        with pytest.raises(MxLedgerReadError) as e:
            await self.mx_ledger_processor.process(mx_ledger_id=uuid.uuid4())

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

        with pytest.raises(MxLedgerInvalidProcessStateError) as e:
            await self.mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)

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
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        error = DataError("Test data error.")
        mocker.patch(
            "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.move_ledger_state_to_processing_and_close_schedule_ledger",
            side_effect=error,
        )
        with pytest.raises(MxLedgerProcessError) as e:
            await self.mx_ledger_processor.process(mx_ledger_id=mx_ledger_id)

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

        # todo: maybe need to fix this later
        class SubOE(OperationalError):
            pgcode = LOCK_NOT_AVAILABLE

        error = SubOE("Test lock not available error")
        mock_process_ledger.side_effect = error

        with pytest.raises(MxLedgerProcessError) as e:
            await self.mx_ledger_processor.process(ledger_id)
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

    async def test_submit_ledger_not_found_raise_exception(self):
        with pytest.raises(MxLedgerReadError) as e:
            await self.mx_ledger_processor.submit(uuid.uuid4())
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_NOT_FOUND
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_NOT_FOUND.value]
        )

    async def test_submit_ledger_invalid_state_raise_exception(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        # prepare an open ledger
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        with pytest.raises(MxLedgerInvalidProcessStateError) as e:
            await self.mx_ledger_processor.submit(ledger_id)
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE
        assert (
            e.value.error_message
            == ledger_error_message_maps[
                LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE.value
            ]
        )

    async def test_submit_positive_balance_mx_ledger_success(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        mx_ledger = await self.mx_ledger_processor.submit(ledger_id)
        assert mx_ledger
        assert mx_ledger.state == MxLedgerStateType.SUBMITTED
        assert mx_ledger.submitted_at is not None

    async def test_submit_zero_balance_mx_ledger_success(
        self, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=0,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        mx_ledger = await self.mx_ledger_processor.submit(ledger_id)
        assert mx_ledger
        assert mx_ledger.id == ledger_id
        assert mx_ledger.state == MxLedgerStateType.PAID
        assert mx_ledger.finalized_at == mx_ledger.updated_at
        assert mx_ledger.amount_paid == 0
        assert mx_ledger.balance == 0

    @patch(
        "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.rollover_negative_balanced_ledger"
    )
    async def test_submit_negative_balance_retry_exceed_attempt_raise_exception(
        self, mock_submit_ledger, mx_ledger_repository: MxLedgerRepository
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        # todo: maybe need to fix this later
        class SubOE(OperationalError):
            pgcode = LOCK_NOT_AVAILABLE

        error = SubOE("Test lock not available error")
        mock_submit_ledger.side_effect = error
        with pytest.raises(MxLedgerSubmissionError) as e:
            await self.mx_ledger_processor.submit(ledger_id)
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

    async def test_submit_negative_balance_data_error_raise_exception(
        self, mocker: pytest_mock.MockFixture, mx_ledger_repository: MxLedgerRepository
    ):
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        error = DataError("Test data error.")
        mocker.patch(
            "app.ledger.repository.mx_ledger_repository.MxLedgerRepository.rollover_negative_balanced_ledger",
            side_effect=error,
        )
        with pytest.raises(MxLedgerSubmissionError) as e:
            await self.mx_ledger_processor.submit(mx_ledger_id=mx_ledger_id)
        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_SUBMIT_ERROR.value]
        )

    async def test_submit_negative_balance_mx_ledger_to_open_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        # prepare pair of open ledger/scheduled_ledger
        open_ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)
        open_mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=open_ledger_id,
            payment_account_id=payment_account_id,
            balance=2000,
        )
        await mx_ledger_repository.insert_mx_ledger(open_mx_ledger_to_insert)
        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=open_ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        rolled_ledger = await self.mx_ledger_processor.submit(ledger_id)
        assert rolled_ledger
        assert rolled_ledger.id == ledger_id
        assert rolled_ledger.state == MxLedgerStateType.ROLLED
        assert rolled_ledger.finalized_at == rolled_ledger.updated_at
        assert rolled_ledger.amount_paid == 0
        assert rolled_ledger.balance == -1500
        assert rolled_ledger.rolled_to_ledger_id == open_ledger_id

        # retrieve and check the updated open ledger
        retrieve_ledger_request = GetMxLedgerByIdInput(id=open_ledger_id)
        updated_open_ledger = await mx_ledger_repository.get_ledger_by_id(
            retrieve_ledger_request
        )
        assert updated_open_ledger
        assert updated_open_ledger.state == MxLedgerStateType.OPEN
        assert updated_open_ledger.balance == 500
        assert updated_open_ledger.amount_paid is None

    async def test_submit_negative_balance_mx_ledger_to_new_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PROCESSING,
            balance=-1500,
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        async with mx_transaction_repository.payment_database.master().transaction() as tx:  # type: DBTransaction
            connection = tx.connection()
            # retrieve and check the updated open ledger
            request = GetMxScheduledLedgerByAccountInput(
                payment_account_id=payment_account_id
            )
            retrieved_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_for_payment_account_id(
                request, connection
            )
            assert retrieved_scheduled_ledger is None

        rolled_ledger = await self.mx_ledger_processor.submit(ledger_id)
        assert rolled_ledger
        assert rolled_ledger.id == ledger_id
        assert rolled_ledger.state == MxLedgerStateType.ROLLED
        assert rolled_ledger.finalized_at == rolled_ledger.updated_at
        assert rolled_ledger.amount_paid == 0
        assert rolled_ledger.balance == -1500

        async with mx_transaction_repository.payment_database.master().transaction() as db_tx:  # type: DBTransaction
            connection = db_tx.connection()
            # retrieve and check the updated open ledger
            retrieved_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_for_payment_account_id(
                request, connection
            )
            assert retrieved_scheduled_ledger
            retrieve_ledger_request = GetMxLedgerByIdInput(
                id=retrieved_scheduled_ledger.ledger_id
            )
        updated_open_ledger = await mx_ledger_repository.get_ledger_by_id(
            retrieve_ledger_request
        )

        assert updated_open_ledger
        assert updated_open_ledger.state == MxLedgerStateType.OPEN
        assert updated_open_ledger.balance == -1500
        assert updated_open_ledger.amount_paid is None

    # todo: need to add exception cases after Min's pr is merged
    async def test_create_mx_ledger_success(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        mx_ledger_processor = MxLedgerProcessor(
            mx_ledger_repo=mx_ledger_repository,
            mx_transaction_repo=mx_transaction_repository,
            log=mocker.Mock(),
        )

        mx_ledger, mx_transaction = await mx_ledger_processor.create_mx_ledger(
            payment_account_id=payment_account_id,
            currency=CurrencyType.USD.value,
            balance=2000,
            type=MxLedgerType.MICRO_DEPOSIT.value,
        )

        assert mx_ledger is not None
        assert mx_ledger.currency == CurrencyType.USD
        assert mx_ledger.balance == 2000
        assert mx_ledger.state == MxLedgerStateType.PROCESSING
        assert mx_ledger.type == MxLedgerType.MICRO_DEPOSIT

        assert mx_transaction is not None
        assert mx_transaction.ledger_id == mx_ledger.id
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MICRO_DEPOSIT

    async def test_create_mx_ledger_data_error_raise_exception(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        error = DataError("Test data error.")
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.create_ledger_and_insert_mx_transaction",
            side_effect=error,
        )
        with pytest.raises(MxLedgerCreationError) as e:
            mx_ledger_processor = MxLedgerProcessor(
                mx_ledger_repo=mx_ledger_repository,
                mx_transaction_repo=mx_transaction_repository,
                log=mocker.Mock(),
            )
            await mx_ledger_processor.create_mx_ledger(
                payment_account_id=payment_account_id,
                currency=CurrencyType.USD.value,
                balance=2000,
                type=MxLedgerType.MICRO_DEPOSIT.value,
            )

        # todo: add logic to confirm the creation would be rolled back when exception caught

        assert e.value.error_code == LedgerErrorCode.MX_LEDGER_CREATE_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_LEDGER_CREATE_ERROR.value]
        )
