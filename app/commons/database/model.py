import asyncio
from dataclasses import dataclass
from typing import List, Optional

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

    _master_url: Secret
    _replica_url: Optional[Secret] = None
    _master: GinoEngine = no_init_field()
    _replica: Optional[GinoEngine] = no_init_field(None)

    async def init(self) -> "Database":
        created_master = await gino.create_engine(self._master_url.value)
        object.__setattr__(self, "_master", created_master)
        if self._replica_url:
            created_replica = await gino.create_engine(self._replica_url.value)
            object.__setattr__(self, "_replica", created_replica)
        return self

    # TODO: may need to tune this to a reasonable number or even beef up a config object
    STATEMENT_TIMEOUT_SEC: int = no_init_field(5)

    def master(self) -> GinoEngine:
        return self._master

    def replica(self) -> GinoEngine:
        return self._replica or self._master

    async def close(self):
        engines = [self._master]
        if self._replica:
            engines.append(self._replica)

        await asyncio.gather([engine.close() for engine in engines])


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

    # TODO add interface to convert instance as dict and ignore unset keys (other than ignore default keys)
