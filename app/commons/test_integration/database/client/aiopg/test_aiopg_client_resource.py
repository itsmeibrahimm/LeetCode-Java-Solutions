import time

import pytest
import contextlib
from aiopg.sa import connection

from app.commons.config.app_config import AppConfig
from app.commons.database.client.aiopg import AioConnection, AioEngine, AioTransaction

pytestmark = [pytest.mark.asyncio]


@pytest.fixture
async def payout_maindb_aio_engine(app_config: AppConfig):
    assert app_config.PAYOUT_MAINDB_MASTER_URL.value
    engine: AioEngine = AioEngine(
        dsn=app_config.PAYOUT_MAINDB_MASTER_URL.value, minsize=2, maxsize=2, debug=True
    )
    await engine.connect()
    async with engine:
        yield engine
    assert engine.closed(), "engine was not closed properly"


async def test_engine_creation(app_config: AppConfig):
    minsize = 5
    assert app_config.PAYOUT_MAINDB_MASTER_URL.value
    engine: AioEngine = AioEngine(
        dsn=app_config.PAYOUT_MAINDB_MASTER_URL.value, minsize=minsize, maxsize=minsize
    )
    assert engine.closed()

    # Test connect
    await engine.connect()
    assert not engine.closed()
    assert not engine.raw_engine.closed
    assert engine.raw_engine.size >= minsize

    # Test disconnect
    await engine.disconnect()
    assert engine.closed()
    assert engine.raw_engine.closed

    # Test context manager
    async with engine:
        assert not engine.closed()
    assert engine.closed()

    # Test terminate engine with open connections and transactions!
    closing_timeout_sec = 0.5
    engine = AioEngine(
        dsn=app_config.PAYOUT_MAINDB_MASTER_URL.value,
        minsize=minsize,
        maxsize=minsize,
        closing_timeout_sec=closing_timeout_sec,
    )
    async with engine:
        assert not engine.closed()
        async with engine.connection() as connection:
            start = time.time()
            # open a transaction but don't close it
            await connection.transaction()
    duration = time.time() - start
    assert (
        duration >= closing_timeout_sec * 0.9
    )  # we should at least wait for this long until termination happens
    assert (
        duration <= closing_timeout_sec * 1.5
    )  # we really shouldn't wait for 1.5x time until it's terminated!
    assert engine.closed()


async def test_engine_acquire_connection(payout_maindb_aio_engine: AioEngine):
    # Test await acquire then use as cxt manager!
    conn2: AioConnection = payout_maindb_aio_engine.connection()

    async with conn2:
        assert not conn2.raw_connection.closed
    assert not conn2._raw_connection

    # Test await connection and use as context manager
    async with payout_maindb_aio_engine.connection() as conn3:
        assert not conn3.raw_connection.closed
    assert not conn3._raw_connection

    # Test use acquire connection as context manager
    async with payout_maindb_aio_engine.connection() as conn4:
        assert not conn4.raw_connection.closed
    assert not conn4._raw_connection


async def test_connection_acquire_contextmanager(payout_maindb_aio_engine: AioEngine):
    async with payout_maindb_aio_engine.connection() as connection:
        # commit
        async with connection.transaction() as alpha:
            validate_aio_transaction_active(alpha)
        validate_aio_transaction_inactive(alpha)
        validate_aio_connection_open(connection)

        # rollback
        with contextlib.suppress(RuntimeError):
            async with connection.transaction() as beta:
                validate_aio_transaction_active(beta)
                raise RuntimeError()
        validate_aio_transaction_inactive(beta)
        validate_aio_connection_open(connection)

        # commit
        async with connection.transaction() as gamma:
            validate_aio_transaction_active(gamma)
        validate_aio_transaction_inactive(gamma)
        validate_aio_connection_open(connection)
    validate_aio_connection_closed(connection)


async def test_connection_acquire_transactions_rollback(
    payout_maindb_aio_engine: AioEngine
):
    async with payout_maindb_aio_engine.connection() as conn2:
        # commit
        alpha = await conn2.transaction()
        validate_aio_transaction_active(alpha)
        await alpha.commit()
        validate_aio_transaction_inactive(alpha)
        validate_aio_connection_open(conn2)

        # rollback
        beta = await conn2.transaction()
        validate_aio_transaction_active(beta)
        await beta.rollback()
        validate_aio_transaction_inactive(beta)
        validate_aio_connection_open(conn2)
    validate_aio_connection_closed(conn2)


async def test_connection_multiple_styles(payout_maindb_aio_engine: AioEngine):
    async with payout_maindb_aio_engine.connection() as connection:
        # await
        alpha = connection.transaction()
        validate_aio_transaction_inactive(alpha)
        await alpha
        validate_aio_transaction_active(alpha)
        await alpha.commit()
        validate_aio_transaction_inactive(alpha)
        validate_aio_connection_open(connection)

        # start
        beta = connection.transaction()
        validate_aio_transaction_inactive(beta)
        await beta.start()
        validate_aio_transaction_active(beta)
        await beta.rollback()
        validate_aio_transaction_inactive(beta)
        validate_aio_connection_open(connection)

        # context manager
        gamma = connection.transaction()
        async with gamma:
            validate_aio_transaction_active(gamma)
        validate_aio_transaction_inactive(gamma)
        validate_aio_connection_open(connection)
    validate_aio_connection_closed(connection)


async def test_engine_acquire_transaction_contextmanager(
    payout_maindb_aio_engine: AioEngine
):
    # Use as cxt manager
    async with payout_maindb_aio_engine.transaction() as tx:
        validate_aio_transaction_active(tx)
        # await tx.commit()
        # validate_aio_transaction_inactive(tx)
        validate_aio_connection_open(tx.connection())
    validate_aio_connection_closed(tx.connection())


async def test_engine_acquire_transaction_await(payout_maindb_aio_engine: AioEngine):
    transaction = await payout_maindb_aio_engine.transaction()
    validate_aio_transaction_active(transaction)
    validate_aio_connection_open(transaction.connection())
    await transaction.rollback()
    validate_aio_connection_closed(transaction.connection())


def validate_aio_connection_open(conn: AioConnection):
    assert conn
    assert conn.raw_connection
    assert not conn.raw_connection.closed


def validate_aio_connection_closed(conn: AioConnection):
    assert conn
    assert conn._raw_connection is None


def validate_aio_transaction_active(tx: AioTransaction):
    assert tx.raw_transaction.is_active
    raw_connection: connection.SAConnection = tx.raw_transaction.connection
    assert raw_connection
    assert raw_connection.in_transaction


def validate_aio_transaction_inactive(tx: AioTransaction):
    assert not tx._raw_transaction or not tx._raw_transaction.is_active
    # raw_connection: connection.SAConnection = tx.raw_transaction.connection
    # assert raw_connection
    # assert not raw_connection.in_transaction
