from typing import Dict, Optional, Type

from gino import Gino

from app.commons.database.model import DBEntity, TableDefinition


def validation_db_entity_and_table_schema(
    db_entity_cls: Type[DBEntity], table_definition_cls: Type[TableDefinition]
):
    db_entity_fields: Dict[str, type] = {
        f.name: f.type_ for f in db_entity_cls.__fields__.values()
    }

    table_definition: TableDefinition = table_definition_cls(db_metadata=Gino())

    table_definition_columns: Dict[str, type] = {
        c.name: c.type.python_type if not c.nullable else Optional[c.type.python_type]
        for c in table_definition.table.columns
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

        if (
            (column_type != field_type)
            and (Optional[field_type] != column_type)  # noqa: W503
            and (field_type != Optional[column_type])  # noqa: W503
        ):
            miss_match_fields[field] = field_type
            expected_fields[field] = column_type

    assert len(miss_match_fields) == 0, (
        f"Discrepancy between {db_entity_cls} and {table_definition_cls}: "
        f"unexpected entity field types={miss_match_fields}, expected field types={expected_fields}"
    )
