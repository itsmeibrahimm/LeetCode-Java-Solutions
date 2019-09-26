from dataclasses import dataclass

from sqlalchemy import Column, DateTime, Text, Integer, Boolean
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class ConsumerChargeTable(TableDefinition):
    name: str = no_init_field("consumer_charge")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))

    # TODO: Determine correct parameter for DateTime
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    # TODO: this is not referenced in DSJ model and does not appeared to be filled in
    # updated_at: Column = no_init_field(Column("updated_at", DateTime(True)))
    # TODO: remove and/or replace after investigating DSJ usage, this is used in GenericForeignKey (puke)
    target_ct_id: Column = no_init_field(Column("target_ct_id", Integer))
    target_id: Column = no_init_field(Column("target_id", Integer))
    idempotency_key: Column = no_init_field(Column("idempotency_key", Text))
    is_stripe_connect_based: Column = no_init_field(
        Column("is_stripe_connect_based", Boolean)
    )
    country_id: Column = no_init_field(Column("country_id", Integer))

    consumer_id: Column = no_init_field(Column("consumer_id", Integer))
    stripe_customer_id: Column = no_init_field(Column("stripe_customer_id", Integer))
    issue_id: Column = no_init_field(Column("issue_id", Integer))

    total: Column = no_init_field(Column("total", Integer))

    original_total: Column = no_init_field(Column("original_total", Integer))
    currency: Column = no_init_field(Column("currency", Text))
