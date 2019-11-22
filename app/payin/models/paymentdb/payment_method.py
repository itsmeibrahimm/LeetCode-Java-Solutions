from dataclasses import dataclass

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PaymentMethodTable(TableDefinition):
    name: str = no_init_field("payment_methods")
    id: Column = no_init_field(Column("id", UUID(as_uuid=True), primary_key=True))
    payer_id: Column = no_init_field(Column("payer_id", UUID(as_uuid=True)))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
