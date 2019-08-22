import asyncio
from typing import Any, List, Mapping, Optional

from aiopg.sa import connection, create_engine, engine, transaction
from aiopg.sa.result import ResultProxy

from app.commons.database.client.interface import (
    DBConnection,
    DBEngine,
    DBTransaction,
    AwaitableTransactionContext,
    AwaitableConnectionContext,
    EngineTransactionContext,
)


class AioTransaction(DBTransaction):

    _raw_transaction: Optional[transaction.Transaction]
    _connection: "AioConnection"

    def __init__(self, connection: "AioConnection"):
        if connection.closed():
            raise ValueError("connection is closed!")
        self._connection = connection
        self._raw_transaction = None

    async def start(self) -> "AioTransaction":
        if not self._raw_transaction:
            _raw_connection: connection.SAConnection = self._connection._raw_connection
            self._raw_transaction = await _raw_connection.begin()
        return self

    async def commit(self):
        if not self.active():
            raise Exception("cannot commit an inactive transaction!")
        await self.raw_transaction.commit()

    async def rollback(self):
        if self.active():
            await self.raw_transaction.rollback()

    def active(self):
        return (
            self._raw_transaction
            and self._raw_transaction.is_active
            and self._raw_transaction._parent.is_active  # aiopg doesn't check it's parent in "is_active" sad...
            and (not self._connection.closed())
        )

    def connection(self) -> "AioConnection":
        return self._connection

    @property
    def raw_transaction(self) -> transaction.Transaction:
        assert self._raw_transaction, "_raw_transaction not initialized"
        return self._raw_transaction

    async def __aenter__(self):
        if not self.active():
            await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        if self.active():
            await self.commit()


class AioConnection(DBConnection):

    _raw_connection: Optional[connection.SAConnection]
    default_timeout: int
    engine: "AioEngine"

    def __init__(self, engine: "AioEngine"):
        if engine.closed():
            raise ValueError("engine is closed!")

        self.engine = engine
        self.default_timeout = self.engine.default_stmt_timeout_sec
        self._raw_connection = None

    async def open(self) -> "AioConnection":
        if not self._raw_connection:
            assert self.engine._raw_engine
            self._raw_connection = await self.engine._raw_engine.acquire()
        return self

    def closed(self):
        return (not self._raw_connection) or self._raw_connection.closed

    async def close(self):
        if not self.closed():
            await self._raw_connection.close()

    def transaction(self) -> AwaitableTransactionContext:
        new_transaction = AioTransaction(connection=self)
        return AwaitableTransactionContext(generator=new_transaction.start)

    async def execute(self, stmt, *, timeout: int = None) -> List[Mapping]:
        _timeout = timeout or self.default_timeout
        result_proxy: ResultProxy = await self.raw_connection.execute(
            stmt, timeout=_timeout
        )
        result: List[Mapping] = []
        if result_proxy.returns_rows:
            result = await result_proxy.fetchall()
        else:
            result_proxy.close()
        return result

    async def fetch_one(self, stmt, *, timeout: int = None) -> Optional[Mapping]:
        _timeout = timeout or self.default_timeout
        result_proxy: ResultProxy = await self.raw_connection.execute(
            stmt, timeout=_timeout
        )
        result: Optional[Mapping] = None
        if result_proxy.returns_rows:
            result = await result_proxy.fetchone()
        else:
            result_proxy.close()
        return result

    async def fetch_all(self, stmt, *, timeout: int = None) -> List[Mapping]:
        _timeout = timeout or self.default_timeout
        result_proxy: ResultProxy = await self.raw_connection.execute(
            stmt, timeout=_timeout
        )
        result: List[Mapping] = []
        if result_proxy.returns_rows:
            result = await result_proxy.fetchall()
        else:
            result_proxy.close()
        return result

    async def fetch_value(self, stmt, *, timeout: int = None):
        _timeout = timeout or self.default_timeout
        return await self.raw_connection.scalar(
            stmt, timeout=_timeout
        )  # result proxy is already closed at this time

    @property
    def raw_connection(self) -> connection.SAConnection:
        assert self._raw_connection, "_raw_connection not initialized"
        return self._raw_connection

    async def __aenter__(self):
        if self.closed():
            await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


class AioEngine(DBEngine):
    id: str
    dsn: str
    minsize: int = 1
    maxsize: int = 1
    connection_timeout_sec: int = 30
    closing_timeout_sec: int = 60

    force_rollback: bool = False
    debug: bool = False
    _raw_engine: Optional[engine.Engine]

    def __init__(
        self,
        dsn: str,
        *,
        id: Optional[str] = None,
        minsize: int = 1,
        maxsize: int = 1,
        connection_timeout_sec: int = 30,
        default_stmt_timeout_sec: int = 30,
        closing_timeout_sec: int = 60,
        force_rollback: bool = False,
        debug: bool = False,
    ):
        if not dsn:
            raise ValueError(f"dsn cannot be empty or None")
        if minsize <= 0:
            raise ValueError(f"minsize should be > 0 but found {minsize}")
        if minsize > maxsize:
            raise ValueError(
                f"maxsize should be >= minsize but found maxsize={maxsize}, minsize={minsize}"
            )
        if connection_timeout_sec <= 0:
            raise ValueError(
                f"connection_timeout_sec should be > 0 but found {connection_timeout_sec}"
            )
        if closing_timeout_sec <= 0:
            raise ValueError(
                f"closing_timeout_sec should be > 0 but found {closing_timeout_sec}"
            )
        if default_stmt_timeout_sec <= 0:
            raise ValueError(
                f"default_stmt_timeout_sec should be > 0 but found {default_stmt_timeout_sec}"
            )

        self.dsn = dsn
        self.minsize = minsize
        self.maxsize = maxsize
        self.connection_timeout_sec = connection_timeout_sec
        self.closing_timeout_sec = closing_timeout_sec
        self.default_stmt_timeout_sec = default_stmt_timeout_sec
        self.id = id if id else "undefined"
        self._raw_engine = None
        self.debug = debug
        self.force_rollback = force_rollback  # TODO actually implement force rollback

    def closed(self):
        return (not self._raw_engine) or self._raw_engine.closed

    async def connect(self) -> "AioEngine":
        if self.closed():
            self._raw_engine = await create_engine(
                dsn=self.dsn,
                minsize=self.minsize,
                maxsize=self.maxsize,
                timeout=self.connection_timeout_sec,
                echo=self.debug,
            )
        return self

    async def disconnect(self):
        if not self.closed():
            self._raw_engine.close()
            try:
                await asyncio.wait_for(
                    self._raw_engine.wait_closed(), timeout=self.closing_timeout_sec
                )
            except Exception:  # No matter what, let's terminate to prevent leaking
                self._raw_engine.terminate()
                await self._raw_engine.wait_closed()

    def acquire(self) -> AwaitableConnectionContext:
        new_connection = AioConnection(engine=self)
        return AwaitableConnectionContext(generator=new_connection.open)

    def transaction(self):
        async def tx_generator() -> AioTransaction:
            opened_conn = await self.acquire()
            return await opened_conn.transaction()

        return EngineTransactionContext(generator=tx_generator)

    async def execute(self, stmt, *, timeout: int = None) -> List[Mapping]:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.execute(stmt, timeout=timeout)
        return result

    async def fetch_one(self, stmt, *, timeout: int = None) -> Optional[Mapping]:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.fetch_one(stmt, timeout=timeout)
        return result

    async def fetch_all(self, stmt, *, timeout: int = None) -> List[Mapping]:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.fetch_all(stmt, timeout=timeout)
        return result

    async def fetch_value(self, stmt, *, timeout: int = None) -> Optional[Any]:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.fetch_value(stmt, timeout=timeout)
        return result

    @property
    def raw_engine(self) -> engine.Engine:
        assert self._raw_engine, "_raw_engine not initialized"
        return self._raw_engine

    async def __aenter__(self):
        if self.closed():
            await self.connect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
