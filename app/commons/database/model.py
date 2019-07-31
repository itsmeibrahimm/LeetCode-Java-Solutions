from dataclasses import dataclass
from typing import List, Optional

from gino import Gino, GinoEngine
from pydantic import BaseModel
from sqlalchemy import Column, Table
from typing_extensions import Protocol

from app.commons.utils.dataclass_extensions import no_init_field


@dataclass(frozen=True)
class TableDefinition:
    """
    Customized wrapper around SqlAlchemy Table object so that we can statically refer to column names and add more
    extensions around table schema
    """

    gino: Gino
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
        object.__setattr__(self, "table", Table(self.name, self.gino, *columns))


@dataclass(frozen=True)
class Database:
    """
    Encapsulate connections pools for a database.

    """

    _master: GinoEngine
    _replica: Optional[GinoEngine] = None

    # TODO: may need to tune this to a reasonable number or even beef up a config object
    STATEMENT_TIMEOUT_SEC: int = no_init_field(5)

    def master(self) -> GinoEngine:
        return self._master

    def replica(self) -> GinoEngine:
        return self._replica or self._master


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


class DBContext(Protocol):
    """
    A context protocol providing access to Database connection resources
    """

    payout_maindb: Database
    # TODO add other db connection here after the pattern is shipped
