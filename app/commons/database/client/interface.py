from abc import ABC, abstractmethod
from typing import (
    Any,
    Awaitable,
    Callable,
    Mapping,
    Optional,
    Sequence,
    TypeVar,
    Generator,
)


class DBResult(Mapping):
    """
    Wrapper interface holding single row returned by database query.
    """

    @property
    @abstractmethod
    def matched_row_count(self) -> int:
        """
        number of row matched by `where` clause if applicable, but **NOT** necessarily rows returned
        """
        pass


DBResultT = TypeVar("DBResultT", bound=DBResult)


class DBMultiResult(ABC, Sequence[DBResultT]):
    """
    Wrapper interface holding multiple rows returned by database query.

    TODO: could add pagination support here when needed
    """

    @property
    @abstractmethod
    def matched_row_count(self) -> int:
        """
        number of row matched by `where` clause if applicable, but **NOT** necessarily rows returned
        """
        pass


class DBTransaction(ABC):
    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass

    @abstractmethod
    def connection(self) -> "DBConnection":
        pass

    @abstractmethod
    def __await__(self) -> Generator:
        pass

    @abstractmethod
    async def __aenter__(self) -> "DBTransaction":
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class DBConnection(ABC):
    @abstractmethod
    def transaction(self) -> DBTransaction:
        pass

    @abstractmethod
    async def execute(self, stmt) -> DBMultiResult:
        pass

    @abstractmethod
    async def fetch_one(self, stmt) -> Optional[DBResult]:
        pass

    @abstractmethod
    async def fetch_all(self, stmt) -> DBMultiResult:
        pass

    @abstractmethod
    async def fetch_value(self, stmt) -> Optional[Any]:
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class EngineTransactionContext:
    __slots__ = ["_transaction", "_generator"]
    _transaction: Optional[DBTransaction]
    _generator: Optional[Callable[[], Awaitable[DBTransaction]]]

    def __init__(self, generator: Callable[[], Awaitable[DBTransaction]]):
        self._generator = generator
        self._transaction = None

    async def __aenter__(self) -> DBTransaction:
        if self._transaction:
            raise Exception("Transaction already initialized")
        if not self._generator:
            raise Exception("Current context already used")
        self._transaction = await self._generator()
        return await self._transaction.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._transaction:
            transaction = self._transaction
            self._transaction = None
            self._generator = None
            await transaction.__aexit__(exc_type, exc_val, exc_tb)
            await transaction.connection().close()


class DBEngine(ABC):
    """
    Encapsulate a set connection pool/engine interfaces.
    Basic usage:
    1. Directly execute statement WITHOUT worrying about closing resource
        result = await engine.fetch_one(stmt, timeout=...)

    2. Acquire connection and execute as you will:
        2.2. async cxt manager style:
            async with engine.acquire() as conn:
                result = await conn.fetch_one(stmt)
            assert conn.closed()
        2.3. mix-and-match!
            conn = engine.acquire()
            async with conn:
                result = await conn.fetch_one(stmt)
            assert conn.closed()

        Reference tests: app.commons.test_integration.database.client.aiopg.test_aiopg_client_resource.test_engine_acquire_connection

    3. Acquire transaction and execute as you will:
        ONLY support via async cxt manager style, as acquire a transaction from engine directly
        will implicitly open a DBConnection so you want to make sure close it and not passing it around.

        e.g.
        async with engine.transaction() as tx:
            conn = tx.connection()
            result = await conn.fetch_all(stmt)

            tx.rollback() (or cxt manager will auto commit for you!)

        Reference tests: app.commons.test_integration.database.client.aiopg.test_aiopg_client_resource.test_connection_acquire_transaction

    4. More use cases demonstrated by:
        4.1 resource management tests:
            app/commons/test_integration/database/client/aiopg/test_aiopg_client_resource.py
        4.2 execution / transaction tests:
            app/commons/test_integration/database/client/aiopg/test_aiopg_client_execution.py

    """

    @abstractmethod
    def closed(self):
        pass

    def is_connected(self):
        return not self.closed()

    @abstractmethod
    async def connect(self):
        pass

    @property
    @abstractmethod
    def dsn(self) -> str:
        pass

    @abstractmethod
    def acquire(self) -> DBConnection:
        pass

    @abstractmethod
    def transaction(self) -> DBTransaction:
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def execute(self, stmt) -> DBMultiResult:
        pass

    @abstractmethod
    async def fetch_one(self, stmt) -> Optional[DBResult]:
        pass

    @abstractmethod
    async def fetch_all(self, stmt) -> DBMultiResult:
        pass

    @abstractmethod
    async def fetch_value(self, stmt) -> Optional[Any]:
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
