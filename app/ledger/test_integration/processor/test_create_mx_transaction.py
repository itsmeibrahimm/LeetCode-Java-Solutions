import asyncio
import uuid
from datetime import datetime, timezone

import pytest
import pytest_mock
from asynctest import patch
from tenacity import RetryError

from app.commons.core.errors import DBDataError, DBOperationLockNotAvailableError
from app.commons.database.infra import DB
from app.commons.types import Currency
from app.ledger.core.data_types import (
    GetMxScheduledLedgerInput,
    GetMxLedgerByIdInput,
    GetMxScheduledLedgerOutput,
    InsertMxTransactionWithLedgerInput,
)
from app.ledger.core.exceptions import (
    MxTransactionCreationError,
    LedgerErrorCode,
    ledger_error_message_maps,
)
from app.ledger.core.mx_transaction.processors.create_mx_transaction import (
    CreateMxTransaction,
    CreateMxTransactionRequest,
)
from app.ledger.core.types import (
    MxScheduledLedgerIntervalType,
    MxLedgerType,
    MxLedgerStateType,
    MxTransactionType,
)
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.ledger.test_integration.utils import (
    prepare_mx_scheduled_ledger,
    prepare_mx_ledger,
)


class TestCreateMxTransaction:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        mocker: pytest_mock.MockFixture,
        mx_transaction_repository: MxTransactionRepository,
    ):
        self.mx_transaction_repo = mx_transaction_repository
        self.mocker = mocker

    def _construct_mx_transaction_op(
        self,
        payment_account_id=str(uuid.uuid4()),
        routing_key=datetime(2019, 8, 1, tzinfo=timezone.utc),
        interval_type=MxScheduledLedgerIntervalType.WEEKLY,
    ):
        return CreateMxTransaction(
            mx_transaction_repo=self.mx_transaction_repo,
            logger=self.mocker.Mock(),
            request=CreateMxTransactionRequest(
                payment_account_id=payment_account_id,
                amount=2000,
                currency=Currency.USD,
                routing_key=routing_key,
                interval_type=interval_type,
                idempotency_key=str(uuid.uuid4()),
                target_type=MxTransactionType.MERCHANT_DELIVERY,
            ),
        )

    @pytest.fixture
    def mx_transaction_repository(
        self, ledger_paymentdb: DB
    ) -> MxTransactionRepository:
        return MxTransactionRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_ledger_repository(self, ledger_paymentdb: DB) -> MxLedgerRepository:
        return MxLedgerRepository(database=ledger_paymentdb)

    @pytest.fixture
    def mx_scheduled_ledger_repository(
        self, ledger_paymentdb: DB
    ) -> MxScheduledLedgerRepository:
        return MxScheduledLedgerRepository(database=ledger_paymentdb)

    async def test_get_open_mx_scheduled_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1, tzinfo=timezone.utc)
        scheduled_ledger_id = uuid.uuid4()

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )
        create_mx_transaction_op = self._construct_mx_transaction_op(
            payment_account_id=payment_account_id
        )
        mx_transaction = await create_mx_transaction_op._execute()
        assert mx_transaction is not None
        assert mx_transaction.ledger_id == ledger_id
        assert mx_transaction.currency == Currency.USD
        assert mx_transaction.routing_key == routing_key
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_scheduled_ledger_request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
        )
        async with mx_transaction_repository._database.master().connection() as connection:
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                get_scheduled_ledger_request, connection
            )
            assert mx_scheduled_ledger is not None

        get_mx_ledger_request = GetMxLedgerByIdInput(id=ledger_id)
        mx_ledger = await mx_ledger_repository.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.balance == 4000

    async def test_get_open_multi_mx_scheduled_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1, tzinfo=timezone.utc)
        closed_at = int(datetime.utcnow().timestamp() * 1000000)

        # construct and insert paid/closed ledger/scheduled_ledger so that it cannot find an open scheduled ledger with given period
        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            state=MxLedgerStateType.PAID,
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            closed_at=closed_at,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        # construct and insert open ledger/scheduled_ledger from (2019-08-12-7:00) to (2019-08-19-7:00)
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 13, tzinfo=timezone.utc),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        # construct and insert open ledger/scheduled_ledger from (2019-08-05-7:00) to (2019-08-12-7:00)
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 7, tzinfo=timezone.utc),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        create_mx_transaction_op = self._construct_mx_transaction_op(
            payment_account_id=payment_account_id
        )
        mx_transaction = await create_mx_transaction_op._execute()
        assert mx_transaction is not None
        assert mx_transaction.ledger_id == ledger_id
        assert mx_transaction.currency == Currency.USD
        assert mx_transaction.routing_key == routing_key
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_mx_ledger_request = GetMxLedgerByIdInput(id=ledger_id)
        mx_ledger = await mx_ledger_repository.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.balance == 4000

    async def test_create_mx_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1, tzinfo=timezone.utc)

        create_mx_transaction_op = self._construct_mx_transaction_op(
            payment_account_id=payment_account_id
        )
        mx_transaction = await create_mx_transaction_op._execute()
        assert mx_transaction is not None
        assert mx_transaction.currency == Currency.USD
        assert mx_transaction.routing_key == routing_key
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_scheduled_ledger_request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
        )
        async with mx_transaction_repository._database.master().connection() as connection:
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                get_scheduled_ledger_request, connection
            )
        assert mx_scheduled_ledger is not None
        assert mx_scheduled_ledger.ledger_id == mx_transaction.ledger_id

        get_mx_ledger_request = GetMxLedgerByIdInput(id=mx_transaction.ledger_id)
        mx_ledger = await mx_ledger_repository.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.balance == 2000

    async def test_insert_txn_and_ledger_raise_data_error(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        error = DBDataError("Test data error.")
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.create_ledger_and_insert_mx_transaction",
            side_effect=error,
        )
        create_mx_transaction_op = self._construct_mx_transaction_op()
        with pytest.raises(MxTransactionCreationError) as e:
            await create_mx_transaction_op._execute()
        assert e.value.error_code == LedgerErrorCode.MX_TXN_CREATE_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_TXN_CREATE_ERROR.value]
        )

    async def test_insert_txn_and_ledger_raise_unique_violate_error(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        # construct and insert ledger/scheduled_ledger
        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=ledger_id,
            routing_key=routing_key,
        )
        inserted_mx_scheduled_ledger = await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        values_for_get_open_mx_scheduled_ledger_with_period = iter(
            [None, inserted_mx_scheduled_ledger]
        )

        @asyncio.coroutine
        def mock_get_open_mx_scheduled_ledger_with_period_results(*args):
            return next(values_for_get_open_mx_scheduled_ledger_with_period)

        @asyncio.coroutine
        def mock_get_open_mx_scheduled_ledger_for_payment_account_id(*args):
            return None

        # To trigger a UniqueViolationError in MxTransactionProcessor.create(), we have to insert a mx_scheduled_ledger
        # first, and mock get_open_mx_scheduled_ledger_with_period and
        # get_open_mx_scheduled_ledger_for_payment_account_id as None to simulate the concurrent mx_scheduled_ledger
        # creations.
        # In the error handling of UniqueViolationError, get_open_mx_scheduled_ledger_with_period is called again, since
        # the same mx_scheduled_ledger is already created. We mock the second get_open_mx_scheduled_ledger_with_period
        # call to return the inserted_mx_scheduled_ledger.
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository"
            ".get_open_mx_scheduled_ledger_with_period",
            side_effect=mock_get_open_mx_scheduled_ledger_with_period_results,
        )
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository."
            "get_open_mx_scheduled_ledger_for_payment_account_id",
            side_effect=mock_get_open_mx_scheduled_ledger_for_payment_account_id,
        )

        create_mx_transaction_op = self._construct_mx_transaction_op(
            payment_account_id=payment_account_id
        )
        mx_transaction = await create_mx_transaction_op._execute()
        assert mx_transaction is not None
        assert mx_transaction.ledger_id == ledger_id

        get_ledger_request = GetMxLedgerByIdInput(id=ledger_id)
        retrieved_mx_ledger = await mx_ledger_repository.get_ledger_by_id(
            get_ledger_request
        )
        assert retrieved_mx_ledger is not None
        assert retrieved_mx_ledger.balance == 4000

    async def test_insert_txn_and_update_ledger_raise_data_error(
        self,
        mocker: pytest_mock.MockFixture,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        error = DBDataError("Test data error.")
        payment_account_id = str(uuid.uuid4())
        mock_mx_scheduled_ledger = GetMxScheduledLedgerOutput(
            id=uuid.uuid4(),
            payment_account_id=payment_account_id,
            ledger_id=uuid.uuid4(),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            closed_at=0,
            start_time=datetime(2019, 8, 5),
            end_time=datetime(2019, 8, 12),
        )

        @asyncio.coroutine
        def mock_coro(*args):
            return mock_mx_scheduled_ledger

        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.insert_mx_transaction_and_update_ledger",
            side_effect=error,
        )
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.get_open_mx_scheduled_ledger_with_period",
            side_effect=mock_coro,
        )
        create_mx_transaction_op = self._construct_mx_transaction_op(
            payment_account_id=payment_account_id
        )
        with pytest.raises(MxTransactionCreationError) as e:
            await create_mx_transaction_op._execute()
        assert e.value.error_code == LedgerErrorCode.MX_TXN_CREATE_ERROR
        assert (
            e.value.error_message
            == ledger_error_message_maps[LedgerErrorCode.MX_TXN_CREATE_ERROR.value]
        )

    async def test_insert_mx_txn_and_update_ledger_balance_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        insert_request = InsertMxTransactionWithLedgerInput(
            currency=Currency.USD,
            amount=1000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=routing_key,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_ledger_repository._database.master().connection() as connection:
            mx_transaction = await mx_transaction_repository.insert_mx_transaction_and_update_ledger(
                request=insert_request, mx_ledger_id=ledger_id, db_connection=connection
            )
        assert mx_transaction is not None
        get_ledger_request = GetMxLedgerByIdInput(id=ledger_id)
        retrieved_ledger = await mx_ledger_repository.get_ledger_by_id(
            get_ledger_request
        )
        assert retrieved_ledger is not None
        assert retrieved_ledger.balance == 3000

    @patch(
        "app.ledger.repository.mx_transaction_repository.MxTransactionRepository"
        ".create_mx_transaction_and_upsert_mx_ledgers"
    )
    async def test_create_mx_transaction_impl_retry_attempt_exceed_raise_exception(
        self, mock_update_ledger
    ):
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)
        interval_type = MxScheduledLedgerIntervalType.WEEKLY

        request_input = InsertMxTransactionWithLedgerInput(
            currency=Currency.USD,
            amount=1000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=interval_type,
            routing_key=routing_key,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        error = DBOperationLockNotAvailableError()
        mock_update_ledger.side_effect = error
        create_mx_transaction_op = self._construct_mx_transaction_op(
            payment_account_id=payment_account_id
        )
        with pytest.raises(RetryError) as e:
            await create_mx_transaction_op._create_mx_transaction_impl(
                request_input=request_input
            )
        assert mock_update_ledger.call_count == e.value.last_attempt.attempt_number
