import sqlalchemy
from enum import Enum
from typing import Dict, Type
from uuid import UUID

from pydantic import Json

from typing import Dict, Type
from app.commons.database.model import DBEntity, TableDefinition

_SPECIAL_TYPE_MAPPING: dict = {UUID: str, Json: dict}


def _unwrap_optional_type(cls: type):
    if hasattr(cls, "__args__"):
        base_type = [
            t for t in cls.__args__ if not issubclass(t, type(None))  # type: ignore
        ]
        return base_type[0]
    return cls


def _get_base_type_if_enum(cls: type):
    if issubclass(cls, Enum):
        return cls.__base__
    return cls


def _normalize_field_type(field_type: type):
    no_optional_type = _unwrap_optional_type(field_type)
    base_type = _get_base_type_if_enum(no_optional_type)
    normalized_type = _SPECIAL_TYPE_MAPPING.get(base_type, base_type)
    return normalized_type


def validation_db_entity_and_table_schema(
    db_entity_cls: Type[DBEntity], table_definition_cls: Type[TableDefinition]
):
    db_entity_fields: Dict[str, type] = {
        f.name: f.type_ for f in db_entity_cls.__fields__.values()
    }

    table_definition: TableDefinition = table_definition_cls(
        db_metadata=sqlalchemy.MetaData()
    )

    table_definition_columns: Dict[str, type] = {
        c.name: c.type.python_type for c in table_definition.table.columns
    }

    db_entity_field_name = set(db_entity_fields.keys())
    table_definition_column_name = set(table_definition_columns.keys())
    unexpected_db_entity_field_name = db_entity_field_name.difference(
        table_definition_column_name
    )

    assert len(unexpected_db_entity_field_name) == 0, (
        f"Discrepancy between {db_entity_cls} and {table_definition_cls}: "
        f"fields existing in db entity but not in table={unexpected_db_entity_field_name}"
    )

    miss_match_fields = {}
    expected_fields = {}

    for field, field_type in db_entity_fields.items():
        column_type = table_definition_columns[field]

        normalized_field_python_type = _normalize_field_type(field_type)

        if column_type != normalized_field_python_type:
            miss_match_fields[field] = field_type
            expected_fields[field] = column_type

    assert len(miss_match_fields) == 0, (
        f"Discrepancy between {db_entity_cls} and {table_definition_cls}: "
        f"unexpected entity field types={miss_match_fields}, expected field types={expected_fields}"
    )
