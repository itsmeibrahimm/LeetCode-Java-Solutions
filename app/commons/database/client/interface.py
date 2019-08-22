from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Optional, List, Mapping, Any


class DBTransaction(ABC):
    @abstractmethod
    async def commit(self):
        pass

    @abstractmethod
    async def rollback(self):
        pass

    @abstractmethod
    async def active(self) -> bool:
        pass

    @abstractmethod
    def connection(self) -> "DBConnection":
        pass

    @abstractmethod
    async def __aenter__(self):
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class AwaitableTransactionContext:
    __slots__ = ["_transaction", "_generator"]
    _transaction: Optional[DBTransaction]
    _generator: Optional[Callable[[], Awaitable[DBTransaction]]]

    def __init__(self, generator: Callable[[], Awaitable[DBTransaction]]):
        self._generator = generator
        self._transaction = None

    async def __aenter__(self):
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

    def __await__(self):
        if self._transaction:
            raise Exception("Transaction already initialized")
        if not self._generator:
            raise Exception("Current context already used")
        generator = self._generator
        self._generator = None
        return generator().__await__()


class DBConnection(ABC):
    @abstractmethod
    def closed(self):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    def transaction(self) -> AwaitableTransactionContext:
        pass

    @abstractmethod
    async def execute(self, stmt) -> List[Mapping]:
        pass

    @abstractmethod
    async def fetch_one(self, stmt) -> Optional[Mapping]:
        pass

    @abstractmethod
    async def fetch_all(self, stmt) -> List[Mapping]:
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


class AwaitableConnectionContext:
    __slots__ = ["_connection", "_generator"]
    _connection: Optional[DBConnection]
    _generator: Optional[Callable[[], Awaitable[DBConnection]]]

    def __init__(self, generator: Callable[[], Awaitable[DBConnection]]):
        self._generator = generator
        self._connection = None

    async def __aenter__(self):
        if self._connection:
            raise Exception("Connection already initialized")
        if not self._generator:
            raise Exception("Current context already used")
        self._connection = await self._generator()
        return await self._connection.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._connection:
            connection = self._connection
            self._connection = None
            self._generator = None
            await connection.__aexit__(exc_type, exc_val, exc_tb)

    def __await__(self):
        if self._connection:
            raise Exception("Connection already initialized")
        if not self._generator:
            raise Exception("Current context already used")
        generator = self._generator
        self._generator = None
        return generator().__await__()


class EngineTransactionContext:
    __slots__ = ["_transaction", "_generator"]
    _transaction: Optional[DBTransaction]
    _generator: Optional[Callable[[], Awaitable[DBTransaction]]]

    def __init__(self, generator: Callable[[], Awaitable[DBTransaction]]):
        self._generator = generator
        self._transaction = None

    async def __aenter__(self):
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
    Encapsulate a set connection pool/engine interfaces
    """

    @abstractmethod
    def closed(self):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    def acquire(self) -> AwaitableConnectionContext:
        pass

    @abstractmethod
    def transaction(self) -> EngineTransactionContext:
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def execute(self, stmt) -> List[Mapping]:
        pass

    @abstractmethod
    async def fetch_one(self, stmt) -> Optional[Mapping]:
        pass

    @abstractmethod
    async def fetch_all(self, stmt) -> List[Mapping]:
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
