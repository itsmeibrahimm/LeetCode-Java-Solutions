from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PgpPaymentMethodTable(TableDefinition):
    name: str = no_init_field("pgp_payment_methods")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    pgp_code: Column = no_init_field(Column("pgp_code", Text))
    pgp_resource_id: Column = no_init_field(Column("pgp_resource_id", Text))
    payer_id: Column = no_init_field(
        Column("payer_id", UUID(as_uuid=True), ForeignKey("payer.id"))
    )
    pgp_card_id: Column = no_init_field(Column("pgp_card_id", Text))
    legacy_consumer_id: Column = no_init_field(Column("legacy_consumer_id", Text))
    object: Column = no_init_field(Column("object", Text))
    type: Column = no_init_field(Column("type", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(False)))
    attached_at: Column = no_init_field(Column("attached_at", DateTime(False)))
    detached_at: Column = no_init_field(Column("detached_at", DateTime(False)))
