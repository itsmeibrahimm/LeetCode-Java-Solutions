from dataclasses import dataclass

from sqlalchemy import Column, Integer, Text, DateTime, Boolean
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class StripeCardTable(TableDefinition):
    name: str = no_init_field("stripe_card")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    stripe_id: Column = no_init_field(Column("stripe_id", Text))
    fingerprint: Column = no_init_field(Column("fingerprint", Text))
    last4: Column = no_init_field(Column("last4", Text))
    dynamic_last4: Column = no_init_field(Column("dynamic_last4", Text))
    exp_month: Column = no_init_field(Column("exp_month", Text))
    exp_year: Column = no_init_field(Column("exp_year", Text))
    type: Column = no_init_field(Column("type", Text))
    country_of_origin: Column = no_init_field(Column("country_of_origin", Text))
    zip_code: Column = no_init_field(Column("zip_code", Text))
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    removed_at: Column = no_init_field(Column("removed_at", DateTime(True)))
    is_scanned: Column = no_init_field(Column("is_scanned", Boolean))
    dd_fingerprint: Column = no_init_field(Column("dd_fingerprint", Text))
    active: Column = no_init_field(Column("active", Boolean))
    consumer_id: Column = no_init_field(Column("consumer_id", Integer))
    stripe_consumer_id: Column = no_init_field(Column("stripe_consumer_id", Integer))
    external_stripe_customer_id: Column = no_init_field(
        Column("external_stripe_customer_id", Text)
    )
    tokenization_method: Column = no_init_field(Column("tokenization_method", Text))
    address_line1_check: Column = no_init_field(Column("address_line1_check", Text))
    address_zip_check: Column = no_init_field(Column("address_zip_check", Text))
    validation_card_id: Column = no_init_field(Column("validation_card_id", Integer))
