import datetime
from dataclasses import dataclass

from sqlalchemy import Boolean, Column, DateTime, Integer, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PaymentAccountTable(TableDefinition):
    name: str = no_init_field("payment_account")
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    account_type: Column = no_init_field(Column("account_type", Text))
    account_id: Column = no_init_field(Column("account_id", Integer))
    entity: Column = no_init_field(Column("entity", Text))
    old_account_id: Column = no_init_field(Column("old_account_id", Integer))
    upgraded_to_managed_account_at: Column = no_init_field(
        Column("upgraded_to_managed_account_at", DateTime(True))
    )
    is_verified_with_stripe: Column = no_init_field(
        Column("is_verified_with_stripe", Boolean)
    )
    transfers_enabled: Column = no_init_field(Column("transfers_enabled", Boolean))
    charges_enabled: Column = no_init_field(Column("charges_enabled", Boolean))
    statement_descriptor: Column = no_init_field(Column("statement_descriptor", Text))
    created_at: Column = no_init_field(
        Column("created_at", DateTime(True), default=datetime.datetime.utcnow)
    )
    payout_disabled: Column = no_init_field(Column("payout_disabled", Boolean))
    resolve_outstanding_balance_frequency: Column = no_init_field(
        Column("resolve_outstanding_balance_frequency", Text)
    )
