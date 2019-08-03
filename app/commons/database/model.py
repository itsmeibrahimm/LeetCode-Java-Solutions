from dataclasses import dataclass
from typing import ClassVar, List, Optional

import gino
from gino import Gino, GinoEngine
from pydantic import BaseModel
from sqlalchemy import Column, Table

from app.commons.config.app_config import Secret
from app.commons.utils.dataclass_extensions import no_init_field


@dataclass(frozen=True)
class TableDefinition:
    """
    Customized wrapper around SqlAlchemy Table object so that we can statically refer to column names and add more
    extensions around table schema
    """

    db_metadata: Gino
    table: Table = no_init_field()
    name: str = no_init_field()

    def __post_init__(self):
        """
        Utilize dataclass post init hook to load any instance attribute
        with sqlalchemy.Column type as a column of delegate Table
        """
        columns: List[Column] = []
        for k in dir(self):
            attribute = self.__getattribute__(k)
            if isinstance(attribute, Column):
                columns.append(attribute)
        object.__setattr__(self, "table", Table(self.name, self.db_metadata, *columns))


@dataclass(frozen=True)
class Database:
    """
    Encapsulate connections pools for a database.

    """

    _POOL_SIZE: ClassVar[int] = 1
    _master: GinoEngine
    _replica: Optional[GinoEngine] = None

    @classmethod
    async def from_url(
        cls, master_url: Secret, replica_url: Optional[Secret] = None
    ) -> "Database":
        # temporarily set poll size=1 here to unblock local dev
        # TODO make pool sizing configurable per environment
        created_master = await gino.create_engine(
            # DO NOT use 'pool_size' here. Asyncpg currently only take in max_size and min_size.
            master_url.value,
            max_size=cls._POOL_SIZE,
            min_size=cls._POOL_SIZE,
        )

        created_replica = None
        if replica_url:
            # temporarily set poll size=1 here to unblock local dev
            created_replica = await gino.create_engine(
                replica_url.value, max_size=cls._POOL_SIZE, min_size=cls._POOL_SIZE
            )

        return cls(_master=created_master, _replica=created_replica)

    # TODO: may need to tune this to a reasonable number or even beef up a config object
    STATEMENT_TIMEOUT_SEC: int = no_init_field(5)

    def master(self) -> GinoEngine:
        return self._master

    def replica(self) -> GinoEngine:
        return self._replica or self._master

    async def close(self):
        await self._master.close()
        if self._replica:
            await self._replica.close()


class DBEntity(BaseModel):
    """
    Base pydantic entity model. Represents a DB entity converted from raw Database row result.
    """

    class Config:
        orm_mode = (
            True
        )  # Allow initiate a pydantic instance from cls.from_orm(<raw DB row response>)
        allow_mutation = False  # Immutable


class DBRequestModel(BaseModel):
    """
    Base pydantic request model. Represents a DB repository request.
    """

    class Config:
        allow_mutation = False  # Immutable
