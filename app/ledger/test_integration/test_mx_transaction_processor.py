import asyncio
from datetime import datetime
import uuid

import pytest
import pytest_mock
from asyncpg import DataError, UniqueViolationError

from app.commons.context.app_context import AppContext
from app.commons.database.infra import DB
from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.data_types import (
    GetMxLedgerByIdInput,
    GetMxScheduledLedgerOutput,
)
from app.ledger.core.mx_transaction.exceptions import (
    MxTransactionCreationError,
    LedgerErrorCode,
    ledger_error_message_maps,
)
from app.ledger.core.mx_transaction.processor import create_mx_transaction_impl
from app.ledger.core.mx_transaction.types import (
    MxScheduledLedgerIntervalType,
    MxLedgerType,
    MxLedgerStateType,
    MxTransactionType,
)
from app.ledger.repository.mx_ledger_repository import (
    MxLedgerRepository,
    InsertMxLedgerInput,
)
from app.ledger.repository.mx_scheduled_ledger_repository import (
    InsertMxScheduledLedgerInput,
    MxScheduledLedgerRepository,
    GetMxScheduledLedgerByLedgerInput,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository


class TestMxTransactionProcessor:
    pytestmark = [pytest.mark.asyncio]

    async def test_get_open_mx_scheduled_ledger_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: DB
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
            dsj_client=mocker.Mock(),
        )
        ledger_repo = MxLedgerRepository(context=app_context)
        scheduled_ledger_repo = MxScheduledLedgerRepository(context=app_context)
        transaction_repo = MxTransactionRepository(context=app_context)
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)
        interval_type = MxScheduledLedgerIntervalType.WEEKLY

        mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
            id=ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=ledger_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
            start_time=datetime(2019, 7, 29, 7),
            end_time=datetime(2019, 8, 5, 7),
        )
        ledger_to_insert = InsertMxLedgerInput(
            id=ledger_id,
            type=MxLedgerType.SCHEDULED.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )
        await ledger_repo.insert_mx_ledger(ledger_to_insert)
        await scheduled_ledger_repo.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )
        mx_transaction = await create_mx_transaction_impl(
            app_context=app_context,
            req_context=mocker.Mock(),
            payment_account_id=payment_account_id,
            amount=2000,
            currency=CurrencyType.USD,
            routing_key=routing_key,
            interval_type=interval_type,
            mx_ledger_repository=ledger_repo,
            mx_scheduled_ledger_repository=scheduled_ledger_repo,
            mx_transaction_repository=transaction_repo,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        assert mx_transaction is not None
        assert mx_transaction.ledger_id == ledger_id
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.routing_key == routing_key
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_scheduled_ledger_request = GetMxScheduledLedgerByLedgerInput(id=ledger_id)
        mx_scheduled_ledger = await scheduled_ledger_repo.get_mx_scheduled_ledger_by_ledger_id(
            get_scheduled_ledger_request
        )
        assert mx_scheduled_ledger is not None

        get_mx_ledger_request = GetMxLedgerByIdInput(id=ledger_id)
        mx_ledger = await ledger_repo.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.balance == 4000

    async def test_get_open_mx_ledger_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: DB
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
            dsj_client=mocker.Mock(),
        )
        ledger_repo = MxLedgerRepository(context=app_context)
        scheduled_ledger_repo = MxScheduledLedgerRepository(context=app_context)
        transaction_repo = MxTransactionRepository(context=app_context)
        ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)
        interval_type = MxScheduledLedgerIntervalType.WEEKLY

        mx_scheduled_ledger_to_insert = InsertMxScheduledLedgerInput(
            id=ledger_id,
            payment_account_id=payment_account_id,
            ledger_id=ledger_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
            start_time=datetime(2019, 7, 29, 7),
            end_time=datetime(2019, 8, 5, 7),
        )
        ledger_to_insert = InsertMxLedgerInput(
            id=ledger_id,
            type=MxLedgerType.SCHEDULED.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.PAID.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )
        ledger_id_correct = uuid.uuid4()
        ledger_to_insert_correct = InsertMxLedgerInput(
            id=ledger_id_correct,
            type=MxLedgerType.SCHEDULED.value,
            currency=CurrencyType.USD.value,
            state=MxLedgerStateType.OPEN.value,
            balance=2000,
            payment_account_id=payment_account_id,
        )

        await ledger_repo.insert_mx_ledger(ledger_to_insert)
        await scheduled_ledger_repo.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )
        await ledger_repo.insert_mx_ledger(ledger_to_insert_correct)

        mx_transaction = await create_mx_transaction_impl(
            app_context=app_context,
            req_context=mocker.Mock(),
            payment_account_id=payment_account_id,
            amount=2000,
            currency=CurrencyType.USD,
            routing_key=routing_key,
            interval_type=interval_type,
            mx_ledger_repository=ledger_repo,
            mx_scheduled_ledger_repository=scheduled_ledger_repo,
            mx_transaction_repository=transaction_repo,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        assert mx_transaction is not None
        assert mx_transaction.ledger_id == ledger_id_correct
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.routing_key == routing_key
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_mx_ledger_request = GetMxLedgerByIdInput(id=ledger_to_insert_correct.id)
        mx_ledger = await ledger_repo.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.balance == 4000

    async def test_create_mx_ledger_success(
        self, mocker: pytest_mock.MockFixture, ledger_paymentdb: DB
    ):
        app_context: AppContext = AppContext(
            log=mocker.Mock(),
            payout_bankdb=mocker.Mock(),
            payin_maindb=mocker.Mock(),
            payin_paymentdb=mocker.Mock(),
            payout_maindb=mocker.Mock(),
            ledger_maindb=mocker.Mock(),
            ledger_paymentdb=ledger_paymentdb,
            stripe=mocker.Mock(),
            dsj_client=mocker.Mock(),
        )
        payment_account_id = str(uuid.uuid4())
        mx_ledger_repository = MxLedgerRepository(context=app_context)
        mx_scheduled_repository = MxScheduledLedgerRepository(context=app_context)
        transaction_repo = MxTransactionRepository(context=app_context)

        mx_transaction = await create_mx_transaction_impl(
            app_context=app_context,
            req_context=mocker.Mock(),
            payment_account_id=payment_account_id,
            amount=2000,
            currency=CurrencyType.USD,
            routing_key=datetime(2019, 8, 1),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            mx_ledger_repository=mx_ledger_repository,
            mx_scheduled_ledger_repository=mx_scheduled_repository,
            mx_transaction_repository=transaction_repo,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        assert mx_transaction is not None
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.routing_key == datetime(2019, 8, 1)
        assert mx_transaction.amount == 2000
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        mx_scheduled_ledger_request = GetMxScheduledLedgerByLedgerInput(
            id=mx_transaction.ledger_id
        )
        mx_scheduled_ledger = await mx_scheduled_repository.get_mx_scheduled_ledger_by_ledger_id(
            mx_scheduled_ledger_request
        )
        assert mx_scheduled_ledger is not None
        assert mx_scheduled_ledger.ledger_id == mx_transaction.ledger_id

        get_mx_ledger_request = GetMxLedgerByIdInput(id=mx_transaction.ledger_id)
        mx_ledger = await mx_ledger_repository.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.balance == 2000

    async def test_insert_txn_and_ledger_raise_data_error(
        self, mocker: pytest_mock.MockFixture, app_context: AppContext
    ):
        error = DataError()
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.create_ledger_and_insert_mx_transaction",
            side_effect=error,
        )
        payment_account_id = str(uuid.uuid4())
        mx_ledger_repository = MxLedgerRepository(context=app_context)
        mx_scheduled_repository = MxScheduledLedgerRepository(context=app_context)
        transaction_repo = MxTransactionRepository(context=app_context)
        with pytest.raises(MxTransactionCreationError) as e:
            await create_mx_transaction_impl(
                app_context=app_context,
                req_context=mocker.Mock(),
                payment_account_id=payment_account_id,
                amount=2000,
                currency=CurrencyType.USD,
                routing_key=datetime(2019, 8, 1),
                interval_type=MxScheduledLedgerIntervalType.WEEKLY,
                mx_ledger_repository=mx_ledger_repository,
                mx_scheduled_ledger_repository=mx_scheduled_repository,
                mx_transaction_repository=transaction_repo,
                idempotency_key=str(uuid.uuid4()),
                target_type=MxTransactionType.MERCHANT_DELIVERY,
            )
            assert e.error_code == LedgerErrorCode.MX_TXN_CREATE_ERROR
            assert (
                e.error_message
                == ledger_error_message_maps[LedgerErrorCode.MX_TXN_CREATE_ERROR.value]
            )

    async def test_insert_txn_and_ledger_raise_unique_violate_error(
        self, mocker: pytest_mock.MockFixture, app_context: AppContext
    ):
        error = UniqueViolationError()
        mocker.patch(
            "app.ledger.repository.mx_transaction_repository.MxTransactionRepository.create_ledger_and_insert_mx_transaction",
            side_effect=error,
        )
        payment_account_id = str(uuid.uuid4())
        mx_ledger_repository = MxLedgerRepository(context=app_context)
        mx_scheduled_repository = MxScheduledLedgerRepository(context=app_context)
        transaction_repo = MxTransactionRepository(context=app_context)

        with pytest.raises(MxTransactionCreationError) as e:
            await create_mx_transaction_impl(
                app_context=app_context,
                req_context=mocker.Mock(),
                payment_account_id=payment_account_id,
                amount=2000,
                currency=CurrencyType.USD,
                routing_key=datetime(2019, 8, 1),
                interval_type=MxScheduledLedgerIntervalType.WEEKLY,
                mx_ledger_repository=mx_ledger_repository,
                mx_scheduled_ledger_repository=mx_scheduled_repository,
                mx_transaction_repository=transaction_repo,
                idempotency_key=str(uuid.uuid4()),
                target_type=MxTransactionType.MERCHANT_DELIVERY,
            )
            assert (
                e.error_code == LedgerErrorCode.MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR
            )
            assert (
                e.error_message
                == ledger_error_message_maps[
                    LedgerErrorCode.MX_LEDGER_CREATE_UNIQUE_VIOLATION_ERROR.value
                ]
            )

    async def test_insert_txn_and_update_ledger_raise_data_error(
        self, mocker: pytest_mock.MockFixture, app_context: AppContext
    ):
        error = DataError()
        payment_account_id = str(uuid.uuid4())
        mock_mx_scheduled_ledger = GetMxScheduledLedgerOutput(
            id=uuid.uuid4(),
            payment_account_id=payment_account_id,
            ledger_id=uuid.uuid4(),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
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
            "app.ledger.repository.mx_scheduled_ledger_repository.MxScheduledLedgerRepository.get_open_mx_scheduled_ledger_for_period",
            side_effect=mock_coro,
        )
        mx_ledger_repository = MxLedgerRepository(context=app_context)
        mx_scheduled_repository = MxScheduledLedgerRepository(context=app_context)
        transaction_repo = MxTransactionRepository(context=app_context)

        with pytest.raises(MxTransactionCreationError) as e:
            await create_mx_transaction_impl(
                app_context=app_context,
                req_context=mocker.Mock(),
                payment_account_id=payment_account_id,
                amount=2000,
                currency=CurrencyType.USD,
                routing_key=datetime(2019, 8, 1),
                interval_type=MxScheduledLedgerIntervalType.WEEKLY,
                mx_ledger_repository=mx_ledger_repository,
                mx_scheduled_ledger_repository=mx_scheduled_repository,
                mx_transaction_repository=transaction_repo,
                idempotency_key=str(uuid.uuid4()),
                target_type=MxTransactionType.MERCHANT_DELIVERY,
            )
            assert e.error_code == LedgerErrorCode.MX_TXN_CREATE_ERROR
            assert (
                e.error_message
                == ledger_error_message_maps[LedgerErrorCode.MX_TXN_CREATE_ERROR.value]
            )
