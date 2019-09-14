import asyncio
from typing import Any, List, Optional, Sequence, Union, overload

from aiopg.sa import connection, create_engine, engine, transaction
from aiopg.sa.result import ResultProxy, RowProxy

from app.commons import timing
from app.commons.database.client.interface import (
    AwaitableConnectionContext,
    AwaitableTransactionContext,
    DBConnection,
    DBEngine,
    DBMultiResult,
    DBResult,
    DBTransaction,
    EngineTransactionContext,
)


class AioResult(DBResult):
    _row_proxy: RowProxy
    _matched_row_count: int

    def __init__(self, row_proxy: RowProxy, matched_row_count: int):
        self._row_proxy = row_proxy
        self._matched_row_count = matched_row_count

    def __getattr__(self, item):
        return self._row_proxy.__getattribute__(item)

    @property
    def matched_row_count(self) -> int:
        return self._matched_row_count

    def __getitem__(self, key):
        return self._row_proxy.__getitem__(key)

    def __len__(self) -> int:
        return len(self._row_proxy)

    def __iter__(self):
        return self._row_proxy.__iter__()


class AioMultiResult(DBMultiResult[AioResult]):
    _results: Sequence[AioResult]
    _matched_row_count: int

    def __init__(self, row_proxies: List[RowProxy], matched_row_count: int):
        self._results = [
            AioResult(row_proxy, matched_row_count=matched_row_count)
            for row_proxy in row_proxies
        ]
        self._matched_row_count = matched_row_count

    @property
    def matched_row_count(self) -> int:
        return self._matched_row_count

    def __len__(self) -> int:
        return len(self._results)

    @overload
    def __getitem__(self, i: int) -> AioResult:
        return self._results[i]

    @overload
    def __getitem__(self, s: slice) -> Sequence[AioResult]:
        return self._results[s]

    def __getitem__(
        self, i: Union[int, slice]
    ) -> Union[AioResult, Sequence[AioResult]]:
        return self._results[i]


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


class AioConnection(DBConnection, timing.Database):
    _raw_connection: Optional[connection.SAConnection]
    engine: "AioEngine"
    database_name: str
    instance_name: str

    def __init__(self, engine: "AioEngine"):
        if engine.closed():
            raise ValueError("engine is closed!")

        self.engine = engine
        self.database_name = engine.database_name
        self.instance_name = engine.instance_name
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

    @timing.track_query
    async def execute(self, stmt) -> AioMultiResult:
        result_proxy: ResultProxy = await self.raw_connection.execute(stmt)
        row_proxies: List[RowProxy] = []
        if result_proxy.returns_rows:
            row_proxies = await result_proxy.fetchall()
        else:
            result_proxy.close()
        return AioMultiResult(row_proxies, matched_row_count=result_proxy.rowcount)

    @timing.track_query
    async def fetch_one(self, stmt) -> Optional[AioResult]:
        result_proxy: ResultProxy = await self.raw_connection.execute(stmt)
        result: Optional[RowProxy] = None
        if result_proxy.returns_rows:
            result = await result_proxy.fetchone()
        else:
            result_proxy.close()
        return AioResult(result, result_proxy.rowcount) if result else None

    @timing.track_query
    async def fetch_all(self, stmt) -> AioMultiResult:
        result_proxy: ResultProxy = await self.raw_connection.execute(stmt)
        row_proxies: List[RowProxy] = []
        if result_proxy.returns_rows:
            row_proxies = await result_proxy.fetchall()
        else:
            result_proxy.close()
        return AioMultiResult(row_proxies, matched_row_count=result_proxy.rowcount)

    @timing.track_query
    async def fetch_value(self, stmt):
        return await self.raw_connection.scalar(
            stmt
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


class AioEngine(DBEngine, timing.Database):
    database_name: str
    instance_name: str
    _dsn: str
    minsize: int
    maxsize: int
    connection_timeout_sec: float
    closing_timeout_sec: float
    default_client_stmt_timeout_sec: float
    force_rollback: bool
    debug: bool
    _raw_engine: Optional[engine.Engine]

    def __init__(
        self,
        dsn: str,
        *,
        database_name: Optional[str] = None,
        instance_name: str = "",
        minsize: int = 1,
        maxsize: int = 1,
        connection_timeout_sec: float = 1,
        default_client_stmt_timeout_sec: float = 1,
        closing_timeout_sec: float = 60,
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
        if closing_timeout_sec < 0:
            raise ValueError(
                f"closing_timeout_sec should be > 0 but found {closing_timeout_sec}"
            )
        if default_client_stmt_timeout_sec <= 0:
            raise ValueError(
                f"default_stmt_timeout_sec should be > 0 but found {default_client_stmt_timeout_sec}"
            )

        self._dsn = dsn
        self.minsize = minsize
        self.maxsize = maxsize
        self.connection_timeout_sec = connection_timeout_sec
        self.closing_timeout_sec = closing_timeout_sec
        self.default_client_stmt_timeout_sec = default_client_stmt_timeout_sec
        self.database_name = database_name if database_name else "undefined"
        self.instance_name = instance_name
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
                # TODO connection_timeout doesn't guarantee connection acquire timeout
                # currently connection_timeout (timeout) is used by aiopg as default statement timeout
                # to init a new DB cursor every time connection.execute(...) is called
                # see: https://github.com/doordash/payment-service/pull/312/files
                timeout=self.default_client_stmt_timeout_sec,
                # timeout=self.connection_timeout_sec,
                echo=self.debug,
                enable_hstore=False,
            )
        return self

    @property
    def dsn(self) -> str:
        return self._dsn

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

    @timing.track_transaction
    def transaction(self):
        async def tx_generator() -> AioTransaction:
            opened_conn = await self.acquire()
            return await opened_conn.transaction()

        return EngineTransactionContext(generator=tx_generator)

    async def execute(self, stmt) -> AioMultiResult:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.execute(stmt)
        return result

    async def fetch_one(self, stmt) -> Optional[AioResult]:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.fetch_one(stmt)
        return result

    async def fetch_all(self, stmt) -> AioMultiResult:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.fetch_all(stmt)
        return result

    async def fetch_value(self, stmt) -> Optional[Any]:
        async with self.acquire() as conn:  # type: AioConnection
            result = await conn.fetch_value(stmt)
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
