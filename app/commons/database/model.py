import json
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping

import sqlalchemy
from pydantic import BaseModel, validate_model
from pydantic.utils import GetterDict
from sqlalchemy import Column, Table
from sqlalchemy.exc import ArgumentError
from sqlalchemy.sql.schema import SchemaItem

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

    def _extract_columns_from_row_record(self, row) -> Mapping:
        """
        Extract row Record fields to table fields.

        :param row:
        :return:
        """
        return {k.name: row[k] for k in self.table.columns if k in row}


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

    class Config:
        allow_mutation = False  # Immutable

    @classmethod
    def from_row(cls, row: Mapping):
        """
        Construct a Pydantic Model from a row/mapping, ignoring extra fields

        see pydantic.BaseModel.from_orm
        """
        obj = RecordDict(row)
        m = cls.__new__(cls)
        values, fields_set, _ = validate_model(m, obj)  # type: ignore
        object.__setattr__(m, "__dict__", values)
        object.__setattr__(m, "__fields_set__", fields_set)
        return m

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)

        # Does not allow specifying an instance of EB entity without any specified field value
        # todo consider move this to a base model shared across payment repo
        if __pydantic_self__.fields and (not __pydantic_self__.__fields_set__):
            raise ValueError(
                f"At least 1 field need to be specified in model={type(__pydantic_self__)}"
            )

        # validate if an optional field is set to None by user and throw error if it is not allowed to do so
        # (add this validation here, it seems pydantic validator doesn't work well with inheritance)
        for field in __pydantic_self__.__fields_set__:
            if (
                __pydantic_self__.__getattribute__(field) is None
                and field in __pydantic_self__.__class__.not_allow_set_none_fields()
            ):
                raise ValueError(f"{field} is not allowed to set as None")

    def __init_subclass__(cls, *args, **kwargs):
        # enforce only None is allowed as default in DB entity
        # since we currently heavily rely on .dict(skip_default=True) to avoid unexpected behavior
        for field in cls.__fields__.values():
            if field.default is not None:
                raise ValueError(
                    f"only default=None is allowed for field, "
                    f"but found field={field.name} default={field.default} model={cls}"
                )

    def _fields_need_json_to_string_conversion(self):
        """
        Pydantic model has Json type, which takes json string
        once model is instantiated, Json field is converted into python obj
        when we use the model to interact with sqlalchemy, we need to
        convert Json fields back to string, otherwise DB exe will throw

        :return:
        """
        return []

    def dict_after_json_to_string(self, *args, **kwargs):
        data_dict = self.dict(*args, **kwargs)
        return {
            key: json.dumps(value)
            if key in self._fields_need_json_to_string_conversion()
            else value
            for (key, value) in data_dict.items()
        }

    @classmethod
    def not_allow_set_none_fields(cls) -> List[str]:
        """
        Override this to provide set of fields that are not allowed to specified as None.
        When specifying a field as Optional, this means user can leave the field unset.
        But this doesn't mean underlying consumer of this model accept None value on this field.
        e.g. statement_descriptor can be left unset when update a payment account so that it will be ignored in update,
        but you shouldn't set it to None as DB schema defined this field cannot be written to None
        """
        return []


class DBRequestModel(BaseModel):
    """
    Base pydantic request model. Represents a DB repository request.
    """

    class Config:
        allow_mutation = False  # Immutable

    def __init__(__pydantic_self__, **data: Any) -> None:
        super().__init__(**data)

        # Does not allow specifying an instance of EB entity without any specified field value
        # todo consider move this to a base model shared across payment repo
        if not __pydantic_self__.__fields_set__:
            raise ValueError(
                f"At least 1 field need to be specified in model={type(__pydantic_self__)}"
            )

    def __init_subclass__(cls, **kwargs):

        # enforce only None is allowed as default in DB request
        # since we currently heavily rely on .dict(skip_default=True) to avoid unexpected behavior
        for field in cls.__fields__.values():
            if field.default is not None:
                raise ValueError(
                    f"only default=None is allowed for field, "
                    f"but found field={field.name} default={field.default} model={cls}"
                )
