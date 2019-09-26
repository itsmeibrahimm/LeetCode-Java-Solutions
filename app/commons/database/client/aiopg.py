import asyncio
import contextlib
from contextvars import ContextVar
from types import TracebackType
from typing import Any, List, Optional, Sequence, Union, Type, overload, Generator

from aiopg.sa import (
    connection as sa_connection,
    create_engine,
    engine,
    transaction as sa_transaction,
)
from aiopg.sa.result import ResultProxy, RowProxy

from app.commons.timing import database as database_timing
from app.commons.database.client.interface import (
    DBConnection,
    DBEngine,
    DBMultiResult,
    DBResult,
    DBTransaction,
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


class AioTransaction(
    DBTransaction, database_timing.Database, database_timing.TrackedTransaction
):
    _raw_transaction: Optional[sa_transaction.Transaction]
    _connection: "AioConnection"
    database_name: str
    instance_name: str

    timing_manager = database_timing.TransactionTimingManager(
        message="transaction complete"
    )
    tracker: Optional[database_timing.QueryTimer]
    stack: Optional[contextlib.ExitStack]

    def __init__(self, connection: "AioConnection"):
        self._connection = connection
        self._raw_transaction = None
        self.database_name = connection.database_name
        self.instance_name = connection.instance_name
        self.tracker = None
        self.stack = None

    def connection(self) -> "AioConnection":
        return self._connection

    @property
    def raw_transaction(self) -> sa_transaction.Transaction:
        assert self._raw_transaction, "_raw_transaction not initialized"
        return self._raw_transaction

    @timing_manager.track_start
    async def start(self) -> "AioTransaction":
        async with self._connection._transaction_lock:
            is_root = not self._connection._transaction_stack
            await self._connection.__aenter__()
            async with self._connection._query_lock:
                if is_root:
                    self._raw_transaction = (
                        await self._connection.raw_connection.begin()
                    )
                else:
                    self._raw_transaction = (
                        await self._connection.raw_connection.begin_nested()
                    )
            self._connection._transaction_stack.append(self)
        return self

    @timing_manager.track_commit
    @database_timing.track_query
    async def commit(self) -> None:
        async with self._connection._transaction_lock:
            assert self._raw_transaction, "transaction has started"
            assert self._connection._transaction_stack[-1] is self
            self._connection._transaction_stack.pop()
            async with self._connection._query_lock:
                await self._raw_transaction.commit()
            self._raw_transaction = None
            await self._connection.__aexit__()

    @timing_manager.track_rollback
    @database_timing.track_query
    async def rollback(
        self,
        exc_type: Optional[Type[BaseException]] = None,
        exc_value: Optional[BaseException] = None,
        traceback: Optional[TracebackType] = None,
    ) -> None:
        async with self._connection._transaction_lock:
            assert self._raw_transaction, "transaction has started"
            assert self._connection._transaction_stack[-1] is self
            self._connection._transaction_stack.pop()
            async with self._connection._query_lock:
                await self._raw_transaction.rollback()
            self._raw_transaction = None
            await self._connection.__aexit__(exc_type, exc_value, traceback)

    def __await__(self) -> Generator:
        """
        Called if using the low-level `transaction = await database.transaction()`
        """
        return self.start().__await__()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        if exc_type:
            await self.rollback(exc_type, exc_value, traceback)
        else:
            await self.commit()


class AioConnection(DBConnection, database_timing.Database):
    _raw_connection: Optional[sa_connection.SAConnection]
    engine: "AioEngine"
    database_name: str
    instance_name: str

    _transaction_stack: List[AioTransaction]

    def __init__(self, engine: "AioEngine"):
        if engine.closed():
            raise ValueError("engine is closed!")

        self.engine = engine
        self.database_name = engine.database_name
        self.instance_name = engine.instance_name
        self._raw_connection = None

        self._connection_lock = asyncio.Lock()
        self._connection_counter = 0

        self._transaction_lock = asyncio.Lock()
        self._transaction_stack = []

        self._query_lock = asyncio.Lock()

    async def __aenter__(self) -> "AioConnection":
        async with self._connection_lock:
            self._connection_counter += 1
            if self._connection_counter == 1:
                assert self._raw_connection is None
                self._raw_connection = await self.engine.raw_engine.acquire()
        return self

    async def __aexit__(
        self,
        exc_type: Type[BaseException] = None,
        exc_value: BaseException = None,
        traceback: TracebackType = None,
    ) -> None:
        async with self._connection_lock:
            assert self._raw_connection is not None
            self._connection_counter -= 1
            if self._connection_counter == 0:
                await self._raw_connection.close()
                self._raw_connection = None

    def transaction(self) -> AioTransaction:
        return AioTransaction(connection=self)

    @database_timing.track_execute
    async def execute(self, stmt) -> AioMultiResult:
        async with self._query_lock:
            result_proxy: ResultProxy = await self.raw_connection.execute(stmt)
            row_proxies: List[RowProxy] = []
            if result_proxy.returns_rows:
                row_proxies = await result_proxy.fetchall()
            else:
                result_proxy.close()
            return AioMultiResult(row_proxies, matched_row_count=result_proxy.rowcount)

    @database_timing.track_execute
    async def fetch_one(self, stmt) -> Optional[AioResult]:
        async with self._query_lock:
            result_proxy: ResultProxy = await self.raw_connection.execute(stmt)
            result: Optional[RowProxy] = None
            if result_proxy.returns_rows:
                result = await result_proxy.fetchone()
            else:
                result_proxy.close()
            return AioResult(result, result_proxy.rowcount) if result else None

    @database_timing.track_execute
    async def fetch_all(self, stmt) -> AioMultiResult:
        async with self._query_lock:
            result_proxy: ResultProxy = await self.raw_connection.execute(stmt)
            row_proxies: List[RowProxy] = []
            if result_proxy.returns_rows:
                row_proxies = await result_proxy.fetchall()
            else:
                result_proxy.close()
            return AioMultiResult(row_proxies, matched_row_count=result_proxy.rowcount)

    @database_timing.track_execute
    async def fetch_value(self, stmt):
        async with self._query_lock:
            return await self.raw_connection.scalar(
                stmt
            )  # result proxy is already closed at this time

    @property
    def raw_connection(self) -> sa_connection.SAConnection:
        assert self._raw_connection, "_raw_connection not initialized"
        return self._raw_connection


class AioEngine(DBEngine, database_timing.Database):
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
        # align with default gunicorn work graceful timeout 30 sec
        # http://docs.gunicorn.org/en/stable/settings.html?highlight=grace#graceful-timeout
        closing_timeout_sec: float = 30,
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

        # Connections are stored as task-local state.
        self._connection_context: ContextVar[AioConnection] = ContextVar(
            "connection_context"
        )

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

    def connection(self) -> AioConnection:
        try:
            return self._connection_context.get()
        except LookupError:
            connection = AioConnection(engine=self)
            self._connection_context.set(connection)
            return connection

    def transaction(self) -> AioTransaction:
        return self.connection().transaction()

    async def execute(self, stmt) -> AioMultiResult:
        async with self.connection() as conn:
            result = await conn.execute(stmt)
        return result

    async def fetch_one(self, stmt) -> Optional[AioResult]:
        async with self.connection() as conn:
            result = await conn.fetch_one(stmt)
        return result

    async def fetch_all(self, stmt) -> AioMultiResult:
        async with self.connection() as conn:
            result = await conn.fetch_all(stmt)
        return result

    async def fetch_value(self, stmt) -> Optional[Any]:
        async with self.connection() as conn:
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
