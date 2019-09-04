import uuid
from datetime import datetime

import psycopg2
import pytest
from psycopg2 import errorcodes

from app.commons.database.client.interface import DBConnection
from app.commons.types import CurrencyType
from app.ledger.core.data_types import (
    GetMxLedgerByIdInput,
    GetMxScheduledLedgerInput,
    InsertMxTransactionWithLedgerInput,
    GetMxScheduledLedgerByAccountInput,
)
from app.ledger.core.types import (
    MxLedgerType,
    MxTransactionType,
    MxScheduledLedgerIntervalType,
)
from app.ledger.repository.mx_ledger_repository import MxLedgerRepository
from app.ledger.repository.mx_scheduled_ledger_repository import (
    MxScheduledLedgerRepository,
)
from app.ledger.repository.mx_transaction_repository import MxTransactionRepository
from app.ledger.test_integration.utils import (
    prepare_mx_ledger,
    prepare_mx_transaction,
    prepare_mx_scheduled_ledger,
)


class TestMxTransactionRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_insert_mx_transaction_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        mx_ledger_id = uuid.uuid4()
        mx_transaction_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        ide_key = str(uuid.uuid4())

        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        mx_transaction_to_insert = await prepare_mx_transaction(
            transaction_id=mx_transaction_id,
            payment_account_id=payment_account_id,
            ledger_id=mx_ledger_id,
            idempotency_key=ide_key,
        )
        mx_transaction = await mx_transaction_repository.insert_mx_transaction(
            mx_transaction_to_insert
        )

        assert mx_transaction.id == mx_transaction_id
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.ledger_id == mx_ledger_id
        assert mx_transaction.amount == 2000
        assert mx_transaction.payment_account_id == payment_account_id
        assert mx_transaction.idempotency_key == ide_key

    async def test_insert_mx_transaction_raise_exception(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        mx_ledger_id = uuid.uuid4()
        mx_transaction_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())

        mx_ledger_to_insert = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(mx_ledger_to_insert)

        mx_transaction_to_insert = await prepare_mx_transaction(
            transaction_id=mx_transaction_id,
            payment_account_id=payment_account_id,
            ledger_id=mx_ledger_id,
        )
        await mx_transaction_repository.insert_mx_transaction(mx_transaction_to_insert)

        with pytest.raises(psycopg2.IntegrityError) as e:
            await mx_transaction_repository.insert_mx_transaction(
                mx_transaction_to_insert
            )
        assert e.value.pgcode == errorcodes.UNIQUE_VIOLATION

    async def test_create_ledger_and_insert_mx_transaction_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)
        request_input = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=routing_key,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        async with mx_ledger_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            created_ledger, created_txn = await mx_transaction_repository.create_ledger_and_insert_mx_transaction(
                request_input, connection
            )
        assert created_txn is not None
        assert created_txn.currency == CurrencyType.USD
        assert created_txn.amount == 2000
        assert created_txn.payment_account_id == payment_account_id
        assert created_txn.routing_key == datetime(2019, 8, 1)
        assert created_txn.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_scheduled_ledger_request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
        )
        async with mx_ledger_repository.payment_database.master().acquire() as db_connection:  # type: DBConnection
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                get_scheduled_ledger_request, db_connection
            )
        assert mx_scheduled_ledger is not None
        assert mx_scheduled_ledger.ledger_id == created_txn.ledger_id

        mx_ledger = await mx_ledger_repository.get_ledger_by_id(
            GetMxLedgerByIdInput(id=created_txn.ledger_id)
        )
        assert mx_ledger is not None
        assert mx_ledger.id == created_ledger.id
        assert mx_ledger.balance == 2000

    async def test_create_ledger_and_insert_mx_transaction_as_micro_deposit(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)
        request_input = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            type=MxTransactionType.MICRO_DEPOSIT,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=routing_key,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        async with mx_ledger_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            created_ledger, created_txn = await mx_transaction_repository.create_ledger_and_insert_mx_transaction(
                request_input, connection
            )
        assert created_txn is not None
        assert created_txn.currency == CurrencyType.USD
        assert created_txn.amount == 2000
        assert created_txn.payment_account_id == payment_account_id
        assert created_txn.routing_key == datetime(2019, 8, 1)
        assert created_txn.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_scheduled_ledger_request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
        )
        async with mx_ledger_repository.payment_database.master().acquire() as db_connection:  # type: DBConnection
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                get_scheduled_ledger_request, db_connection
            )
        assert mx_scheduled_ledger is None

        get_mx_ledger_request = GetMxLedgerByIdInput(id=created_txn.ledger_id)
        mx_ledger = await mx_ledger_repository.get_ledger_by_id(get_mx_ledger_request)
        assert mx_ledger is not None
        assert mx_ledger.id == created_ledger.id
        assert mx_ledger.balance == 2000

    async def test_create_ledger_and_insert_mx_transaction_raise_exception(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        # test raise error if insert mx_scheduled_ledger failed due to duplicate [payment_account_id, start_time, end_time, closed_at]
        mx_ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)

        ledger_request = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_request)

        scheduled_ledger_request = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            routing_key=routing_key,
            payment_account_id=payment_account_id,
            ledger_id=mx_ledger_id,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            scheduled_ledger_request
        )

        request_input = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=routing_key,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        with pytest.raises(psycopg2.IntegrityError) as e:
            async with mx_ledger_repository.payment_database.master().acquire() as connection:  # type: DBConnection
                await mx_transaction_repository.create_ledger_and_insert_mx_transaction(
                    request_input, connection
                )
        assert e.value.pgcode == errorcodes.UNIQUE_VIOLATION

    async def test_create_ledger_and_insert_mx_transaction_raise_exception_with_scheduled_type_and_without_interval_type(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        routing_key = datetime(2019, 8, 1)
        request_input = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        with pytest.raises(Exception) as e:
            async with mx_ledger_repository.payment_database.master().acquire() as connection:
                await mx_transaction_repository.create_ledger_and_insert_mx_transaction(
                    request_input, connection
                )
        assert (
            e.value.args[0]
            == "interval_type is required when leger type is in MX_LEDGER_TYPE_MUST_HAVE_MX_SCHEDULED_LEDGER"
        )

    async def test_insert_mx_transaction_and_update_ledger_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        # create a new mx_ledger which needs to be updated later
        mx_ledger_id = uuid.uuid4()
        payment_account_id = str(uuid.uuid4())

        ledger_request = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        mx_ledger = await mx_ledger_repository.insert_mx_ledger(ledger_request)

        request_input = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 1),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )

        async with mx_ledger_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            mx_transaction = await mx_transaction_repository.insert_mx_transaction_and_update_ledger(
                request_input, mx_ledger.id, connection
            )
        assert mx_transaction is not None
        assert mx_transaction.currency == CurrencyType.USD
        assert mx_transaction.amount == 2000
        assert mx_transaction.payment_account_id == payment_account_id
        assert mx_transaction.routing_key == datetime(2019, 8, 1)
        assert mx_transaction.target_type == MxTransactionType.MERCHANT_DELIVERY

        get_mx_ledger_request = GetMxLedgerByIdInput(id=mx_transaction.ledger_id)
        mx_ledger_retrieved = await mx_ledger_repository.get_ledger_by_id(
            get_mx_ledger_request
        )
        assert mx_ledger_retrieved is not None
        assert mx_ledger_retrieved.balance == 4000

    async def test_insert_mx_transaction_and_update_ledger_raise_exception(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        # test roll back created_mx_ledger if insert mx_txn failed due to duplicate [payment_account_id, idempotency_key]
        payment_account_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        mx_ledger_id = uuid.uuid4()
        txn_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        ledger_request = await prepare_mx_ledger(
            ledger_id=mx_ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_request)

        insert_txn_request = await prepare_mx_transaction(
            transaction_id=txn_id,
            payment_account_id=payment_account_id,
            ledger_id=mx_ledger_id,
            idempotency_key=idempotency_key,
            routing_key=routing_key,
        )
        await mx_transaction_repository.insert_mx_transaction(insert_txn_request)

        request_input = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            type=MxLedgerType.SCHEDULED,
            payment_account_id=payment_account_id,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=routing_key,
            idempotency_key=idempotency_key,
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        with pytest.raises(Exception):
            async with mx_ledger_repository.payment_database.master().acquire() as connection:  # type: DBConnection
                await mx_transaction_repository.insert_mx_transaction_and_update_ledger(
                    request_input, mx_ledger_id, connection
                )
            # the mx_ledger that needs to be updated should not be updated
            get_ledger_request = GetMxLedgerByIdInput(id=mx_ledger_id)
            mx_ledger_retrieved = await mx_ledger_repository.get_ledger_by_id(
                get_ledger_request
            )
            assert mx_ledger_retrieved is not None
            assert mx_ledger_retrieved.balance == 2000

    async def test_get_open_mx_scheduled_ledger_with_period_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        mx_scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 1)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=routing_key,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                request, connection
            )
            assert mx_scheduled_ledger is not None
            assert mx_scheduled_ledger.id == mx_scheduled_ledger_id
            assert mx_scheduled_ledger.payment_account_id == payment_account_id
            assert mx_scheduled_ledger.ledger_id == ledger_id
            assert (
                mx_scheduled_ledger.interval_type
                == MxScheduledLedgerIntervalType.WEEKLY
            )
            assert mx_scheduled_ledger.start_time == datetime(2019, 7, 29, 7)
            assert mx_scheduled_ledger.end_time == datetime(2019, 8, 5, 7)

    async def test_get_open_mx_scheduled_ledger_with_period_not_exist_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        mx_scheduled_ledger_id = uuid.uuid4()
        routing_key = datetime(2019, 8, 7)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=mx_scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            routing_key=routing_key,
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 1),
            interval_type=MxScheduledLedgerIntervalType.WEEKLY.value,
        )

        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                request, connection
            )
            assert mx_scheduled_ledger is None

    async def test_get_open_mx_scheduled_ledger_with_period_multiple_same_start_time_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        # construct two scheduled_ledgers with same start_time and diff end_time along with ledgers
        payment_account_id = str(uuid.uuid4())
        ledger_id = uuid.uuid4()
        scheduled_ledger_id = uuid.uuid4()
        start_time = datetime(2019, 7, 29, 7)

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)

        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id,
            ledger_id=ledger_id,
            payment_account_id=payment_account_id,
            start_time=start_time,
            end_time=datetime(2019, 8, 5, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

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
            interval_type=MxScheduledLedgerIntervalType.DAILY,
            start_time=start_time,
            end_time=datetime(2019, 7, 30, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        # construct request and retrieve scheduled_ledger
        request = GetMxScheduledLedgerInput(
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 7, 30),
            interval_type=MxScheduledLedgerIntervalType.DAILY.value,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            mx_scheduled_ledger_retrieved = await mx_transaction_repository.get_open_mx_scheduled_ledger_with_period(
                request, connection
            )
            assert mx_scheduled_ledger_retrieved is not None

            assert mx_scheduled_ledger_retrieved.id == scheduled_ledger_id
            assert mx_scheduled_ledger_retrieved.start_time == start_time
            assert mx_scheduled_ledger_retrieved.end_time == datetime(2019, 7, 30, 7)
            assert (
                mx_scheduled_ledger_retrieved.payment_account_id == payment_account_id
            )
            assert (
                mx_scheduled_ledger_retrieved.payment_account_id == payment_account_id
            )
            assert mx_scheduled_ledger_retrieved.ledger_id == ledger_id
            assert (
                mx_scheduled_ledger_retrieved.interval_type
                == MxScheduledLedgerIntervalType.DAILY
            )
            assert mx_scheduled_ledger_retrieved.closed_at == 0

    async def test_get_open_mx_scheduled_ledger_for_payment_account_id_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        scheduled_ledger_id_1 = uuid.uuid4()
        scheduled_ledger_id_2 = uuid.uuid4()
        ledger_id_1 = uuid.uuid4()
        ledger_id_2 = uuid.uuid4()

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id_1, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)
        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id_1,
            ledger_id=ledger_id_1,
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 7),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        ledger_to_insert = await prepare_mx_ledger(
            ledger_id=ledger_id_2, payment_account_id=payment_account_id
        )
        await mx_ledger_repository.insert_mx_ledger(ledger_to_insert)
        mx_scheduled_ledger_to_insert = await prepare_mx_scheduled_ledger(
            scheduled_ledger_id=scheduled_ledger_id_2,
            ledger_id=ledger_id_2,
            payment_account_id=payment_account_id,
            routing_key=datetime(2019, 8, 14),
        )
        await mx_scheduled_ledger_repository.insert_mx_scheduled_ledger(
            mx_scheduled_ledger_to_insert
        )

        request = GetMxScheduledLedgerByAccountInput(
            payment_account_id=payment_account_id
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_for_payment_account_id(
                request, connection
            )

            assert mx_scheduled_ledger is not None
            assert mx_scheduled_ledger.id == scheduled_ledger_id_1
            assert mx_scheduled_ledger.payment_account_id == payment_account_id
            assert mx_scheduled_ledger.ledger_id == ledger_id_1
            assert (
                mx_scheduled_ledger.interval_type
                == MxScheduledLedgerIntervalType.WEEKLY
            )
            assert mx_scheduled_ledger.start_time == datetime(2019, 8, 5, 7)
            assert mx_scheduled_ledger.end_time == datetime(2019, 8, 12, 7)

    async def test_get_open_mx_scheduled_ledger_for_payment_account_not_exist_success(
        self,
        mx_scheduled_ledger_repository: MxScheduledLedgerRepository,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        scheduled_ledger_id = uuid.uuid4()
        ledger_id = uuid.uuid4()
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

        request = GetMxScheduledLedgerByAccountInput(
            payment_account_id=str(uuid.uuid4())
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            mx_scheduled_ledger = await mx_transaction_repository.get_open_mx_scheduled_ledger_for_payment_account_id(
                request, connection
            )
            assert mx_scheduled_ledger is None

    async def test_upsert_mx_transaction_with_same_periods_and_route_to_same_ledgers_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        # prepare mx_transaction with routing_key as datetime(2019, 8, 1) and insert
        insert_txn_request = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            payment_account_id=payment_account_id,
            type=MxLedgerType.SCHEDULED,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 1),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            first_mx_transaction = await mx_transaction_repository.create_mx_transaction_and_upsert_mx_ledgers(
                insert_txn_request, connection
            )

        # prepare another mx_transaction with routing_key as datetime(2019, 8, 2) and insert
        second_insert_txn_request = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            payment_account_id=payment_account_id,
            type=MxLedgerType.SCHEDULED,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 2),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as db_connection:  # type: DBConnection
            second_mx_transaction = await mx_transaction_repository.create_mx_transaction_and_upsert_mx_ledgers(
                second_insert_txn_request, db_connection
            )

        assert first_mx_transaction.ledger_id == second_mx_transaction.ledger_id

    async def test_upsert_mx_transaction_with_multiple_periods_and_route_to_different_ledgers_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        # prepare mx_transaction with routing_key as datetime(2019, 8, 1) and insert
        insert_txn_request = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            payment_account_id=payment_account_id,
            type=MxLedgerType.SCHEDULED,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 1),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            first_mx_transaction = await mx_transaction_repository.create_mx_transaction_and_upsert_mx_ledgers(
                insert_txn_request, connection
            )

        # prepare another mx_transaction with routing_key as datetime(2019, 8, 10) and insert
        second_insert_txn_request = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            payment_account_id=payment_account_id,
            type=MxLedgerType.SCHEDULED,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 10),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as db_connection:  # type: DBConnection
            second_mx_transaction = await mx_transaction_repository.create_mx_transaction_and_upsert_mx_ledgers(
                second_insert_txn_request, db_connection
            )

        assert not first_mx_transaction.ledger_id == second_mx_transaction.ledger_id

    async def test_upsert_mx_transaction_with_multiple_periods_and_route_to_same_ledgers_success(
        self,
        mx_ledger_repository: MxLedgerRepository,
        mx_transaction_repository: MxTransactionRepository,
    ):
        payment_account_id = str(uuid.uuid4())
        # prepare mx_transaction with routing_key as datetime(2019, 8, 10) and insert
        insert_txn_request = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            payment_account_id=payment_account_id,
            type=MxLedgerType.SCHEDULED,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 10),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as connection:  # type: DBConnection
            first_mx_transaction = await mx_transaction_repository.create_mx_transaction_and_upsert_mx_ledgers(
                insert_txn_request, connection
            )

        # prepare another mx_transaction with routing_key as datetime(2019, 8, 1) and insert
        second_insert_txn_request = InsertMxTransactionWithLedgerInput(
            currency=CurrencyType.USD,
            amount=2000,
            payment_account_id=payment_account_id,
            type=MxLedgerType.SCHEDULED,
            interval_type=MxScheduledLedgerIntervalType.WEEKLY,
            routing_key=datetime(2019, 8, 1),
            idempotency_key=str(uuid.uuid4()),
            target_type=MxTransactionType.MERCHANT_DELIVERY,
        )
        async with mx_transaction_repository.payment_database.master().acquire() as db_connection:  # type: DBConnection
            second_mx_transaction = await mx_transaction_repository.create_mx_transaction_and_upsert_mx_ledgers(
                second_insert_txn_request, db_connection
            )

        assert first_mx_transaction.ledger_id == second_mx_transaction.ledger_id
