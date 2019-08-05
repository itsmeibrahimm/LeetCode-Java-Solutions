from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, ForeignKey, Integer
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PgpPaymentMethodTable(TableDefinition):
    name: str = no_init_field("pgp_payment_methods")
    id: Column = no_init_field(Column("id", Text, primary_key=True))
    pgp_code: Column = no_init_field(Column("pgp_code", Text))
    pgp_resource_id: Column = no_init_field(Column("pgp_resource_id", Text))
    payer_id: Column = no_init_field(Column("payer_id", Text, ForeignKey("payer.id")))

    pgp_card_id: Column = no_init_field(Column("pgp_card_id", Text))

    legacy_stripe_card_serial_id: Column = no_init_field(
        Column("legacy_stripe_card_serial_id", Integer)
    )
    legacy_consumer_id: Column = no_init_field(Column("legacy_consumer_id", Text))
    object: Column = no_init_field(Column("object", Text))
    type: Column = no_init_field(Column("type", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(False)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(False)))
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(False)))
    attached_at: Column = no_init_field(Column("deleted_at", DateTime(False)))
    detached_at: Column = no_init_field(Column("deleted_at", DateTime(False)))
