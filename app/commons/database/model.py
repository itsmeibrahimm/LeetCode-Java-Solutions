from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

import sqlalchemy
from pydantic import BaseModel, validate_model
from pydantic.utils import GetterDict
from sqlalchemy import Column, Table
from sqlalchemy.sql.schema import SchemaItem
from sqlalchemy.exc import ArgumentError

from app.commons.utils.dataclass_extensions import no_init_field


@dataclass(frozen=True)
class TableDefinition:
    """
    Customized wrapper around SqlAlchemy Table object so that we can statically refer to column names and add more
    extensions around table schema
    """

    db_metadata: sqlalchemy.MetaData
    table: Table = no_init_field()
    name: str = no_init_field()

    # Additional positional SchemaItem args passed to creating a Sqlalchemy table
    # See https://docs.sqlalchemy.org/en/13/core/metadata.html#sqlalchemy.schema.Table
    additional_schema_args: List[SchemaItem] = no_init_field([])

    # Additional kwargs passed to creating a Sqlalchemy table
    # See https://docs.sqlalchemy.org/en/13/core/metadata.html#sqlalchemy.schema.Table
    additional_schema_kwargs: Dict[str, Any] = no_init_field({})

    def _validate_column(self, column: Column):
        if column.default is not None:
            raise ArgumentError(
                f"Application-level defaults are not supported; they must be manually specified in INSERT statements.\n"
                "See: https://github.com/encode/databases/issues/72\n"
                f"Column '{column.name}' in table '{self.name}' has "
                f"application-level default specified: {repr(column.default)}"
            )

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
                self._validate_column(attribute)
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


class RecordDict(GetterDict):
    """
    wrapper to ignore extra params when constructing DBEntities from rows
    """

    _obj: Mapping

    def get(self, item, default):
        return self._obj.get(item, default)


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

    @classmethod
    def from_row(cls, row: Mapping):
        """
        Construct a Pydantic Model from a row/mapping, ignoring extra fields
        """
        obj = RecordDict(row)
        m = cls.__new__(cls)
        values, fields_set, _ = validate_model(m, obj)  # type: ignore
        object.__setattr__(m, "__values__", values)
        object.__setattr__(m, "__fields_set__", fields_set)
        return m

    class Config:
        allow_mutation = False  # Immutable


class DBRequestModel(BaseModel):
    """
    Base pydantic request model. Represents a DB repository request.
    """

    class Config:
        allow_mutation = False  # Immutable
