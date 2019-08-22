import time

import pytest
from aiopg.sa import connection

from app.commons.config.app_config import AppConfig
from app.commons.database.client.aiopg import AioConnection, AioEngine, AioTransaction
from app.commons.database.client.interface import (
    AwaitableConnectionContext,
    EngineTransactionContext,
)

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
    closing_timeout_sec = 10
    engine = AioEngine(
        dsn=app_config.PAYOUT_MAINDB_MASTER_URL.value,
        minsize=minsize,
        maxsize=minsize,
        closing_timeout_sec=closing_timeout_sec,
    )
    async with engine:
        assert not engine.closed()
        connection = await engine.acquire()
        tx = await connection.transaction()
        start = time.time()
    duration = time.time() - start
    assert (
        duration >= closing_timeout_sec * 0.9
    )  # we should at least wait for this long until termination happens
    assert (
        duration <= closing_timeout_sec * 1.5
    )  # we really shouldn't wait for 1.5x time until it's terminated!
    assert connection.closed()
    assert engine.closed()
    assert not tx.active()


async def test_engine_acquire_connection(payout_maindb_aio_engine: AioEngine):

    # Test no context manager
    connection: AioConnection = await payout_maindb_aio_engine.acquire()
    assert not connection.closed()
    assert not connection.raw_connection.closed

    await connection.close()
    assert connection.closed()
    assert connection.raw_connection.closed

    # Test await connection and use as context manager
    conn_cxt: AwaitableConnectionContext = payout_maindb_aio_engine.acquire()
    async with conn_cxt as connection:
        assert not connection.closed()
        assert not connection.raw_connection.closed
    assert connection.closed()
    assert connection.raw_connection.closed

    # Test use acquire connection as context manager
    async with payout_maindb_aio_engine.acquire() as conn:  # type: AioConnection
        assert not conn.closed()
        assert not conn.raw_connection.closed
    assert conn.closed()
    assert conn.raw_connection.closed


async def test_connection_acquire_transaction(payout_maindb_aio_engine: AioEngine):

    async with payout_maindb_aio_engine.acquire() as conn1:  # type: AioConnection
        async with conn1.transaction() as tx1:  # type: AioTransaction
            validate_aio_transaction_active(tx1)
            await tx1.commit()
            validate_aio_transaction_inactive(tx1)
        validate_aio_connection_open(conn1)

        async with conn1.transaction() as tx2:
            validate_aio_transaction_active(tx2)
            await tx2.rollback()
            validate_aio_transaction_inactive(tx2)
        validate_aio_connection_open(conn1)

        async with conn1.transaction() as tx3:
            validate_aio_transaction_active(tx3)
        validate_aio_transaction_inactive(tx3)
        validate_aio_connection_open(conn1)
    validate_aio_connection_closed(conn1)

    async with payout_maindb_aio_engine.acquire() as conn2:
        tx1 = await conn2.transaction()
        validate_aio_transaction_active(tx1)
        await tx1.commit()
        validate_aio_transaction_inactive(tx1)
        validate_aio_connection_open(conn2)

        tx2 = await conn2.transaction()
        validate_aio_transaction_active(tx2)
        await tx2.rollback()
        validate_aio_transaction_inactive(tx2)
        validate_aio_connection_open(conn2)
    validate_aio_connection_closed(conn2)

    async with payout_maindb_aio_engine.acquire() as conn3:
        tx1_cxt = conn3.transaction()
        async with tx1_cxt as tx1:
            validate_aio_transaction_active(tx1)
            await tx1.commit()
            validate_aio_transaction_inactive(tx1)
        validate_aio_connection_open(conn3)

        tx2_cxt = conn3.transaction()
        async with tx2_cxt as tx2:
            validate_aio_transaction_active(tx2)
            await tx2.rollback()
            validate_aio_transaction_inactive(tx2)
        validate_aio_connection_open(conn3)

        tx3_cxt = conn3.transaction()
        async with tx3_cxt as tx3:
            validate_aio_transaction_active(tx3)
        validate_aio_transaction_inactive(tx3)
        validate_aio_connection_open(conn3)
    validate_aio_connection_closed(conn3)


async def test_engine_acquire_transaction(payout_maindb_aio_engine: AioEngine):

    # Use as cxt manager
    async with payout_maindb_aio_engine.transaction() as tx:  # type: AioTransaction
        validate_aio_transaction_active(tx)
        await tx.commit()
        validate_aio_transaction_inactive(tx)
        validate_aio_connection_open(tx.connection())
    validate_aio_connection_closed(tx.connection())

    # engine transaction can only be used as cxt manager to avoid connection leaking
    cxt: EngineTransactionContext = payout_maindb_aio_engine.transaction()
    assert not hasattr(cxt, "__await__")
    assert not cxt._transaction


def validate_aio_connection_open(conn: AioConnection):
    assert conn
    assert not conn.closed()
    assert conn.raw_connection
    assert not conn.raw_connection.closed


def validate_aio_connection_closed(conn: AioConnection):
    assert conn
    assert conn.closed()
    assert conn.raw_connection
    assert conn.raw_connection.closed


def validate_aio_transaction_active(tx: AioTransaction):
    assert tx.active()
    assert tx.raw_transaction.is_active
    raw_connection: connection.SAConnection = tx.raw_transaction.connection
    assert raw_connection
    assert raw_connection.in_transaction


def validate_aio_transaction_inactive(tx: AioTransaction):
    assert not tx.active()
    assert not tx.raw_transaction.is_active
    raw_connection: connection.SAConnection = tx.raw_transaction.connection
    assert raw_connection
    assert not raw_connection.in_transaction
