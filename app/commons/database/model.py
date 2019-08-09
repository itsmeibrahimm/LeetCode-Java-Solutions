from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import gino
from gino import Gino, GinoEngine
from pydantic import BaseModel
from sqlalchemy import Column, Table
from sqlalchemy.sql.schema import SchemaItem

from app.commons.config.app_config import Secret
from app.commons.database.config import DatabaseConfig
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

    # Additional positional SchemaItem args passed to creating a Sqlalchemy table
    # See https://docs.sqlalchemy.org/en/13/core/metadata.html#sqlalchemy.schema.Table
    additional_schema_args: List[SchemaItem] = no_init_field([])

    # Additional kwargs passed to creating a Sqlalchemy table
    # See https://docs.sqlalchemy.org/en/13/core/metadata.html#sqlalchemy.schema.Table
    additional_schema_kwargs: Dict[str, Any] = no_init_field({})

    def __post_init__(self):
        """
        Utilize dataclass post init hook to load any instance attribute
        with sqlalchemy.Column type as a column of delegate Table
        """
        sa_schema_positional_args: List[SchemaItem] = []
        # Append Column instances first
        for k in dir(self):
            attribute = self.__getattribute__(k)
            if isinstance(attribute, Column):
                sa_schema_positional_args.append(attribute)
        # Then append other schema items
        sa_schema_positional_args.extend(self.additional_schema_args)

        object.__setattr__(
            self,
            "table",
            Table(
                self.name,
                self.db_metadata,
                *sa_schema_positional_args,
                **self.additional_schema_kwargs,
            ),
        )


@dataclass(frozen=True)
class Database:
    """
    Encapsulate connections pools for a database.

    """

    _master: GinoEngine
    _replica: Optional[GinoEngine] = None

    @classmethod
    async def create(
        cls,
        *,
        name: str,
        db_config: DatabaseConfig,
        master_url: Secret,
        replica_url: Optional[Secret] = None,
    ) -> "Database":
        created_master = await gino.create_engine(
            # DO NOT use 'pool_size' here. Asyncpg currently only take in max_size and min_size.
            master_url.value,
            max_size=db_config.master_pool_size,
            min_size=db_config.master_pool_size,
            echo=db_config.debug,
            logging_name=f"{name}_master",
        )

        created_replica = None
        if replica_url:
            created_replica = await gino.create_engine(
                replica_url.value,
                max_size=db_config.replica_pool_size,
                min_size=db_config.replica_pool_size,
                echo=db_config.debug,
                logging_name=f"{name}_replica",
            )

        return cls(_master=created_master, _replica=created_replica)

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

    Note: a subclass of DBEntity need to conform two restrictions determined by the Table schema it's associated to:
    1. all field names is subset of table's column names
    2. python type of each field is exactly same as corresponding table column's python type
    with the exception of field's nullability

    These any newly implemented subclass of DBEntity should be tested
    via :func:`app.tests.commons.database.model.validation_db_entity_and_table_schema`
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
