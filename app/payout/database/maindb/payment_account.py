import attr
from gino import Gino
from sqlalchemy import Boolean, Column, DateTime, Integer, Table, Text
from typing_extensions import final

from app.commons.database.table import TableDefinition
from app.commons.utils.attr_extensions import no_init_attrib


@final
@attr.s(frozen=True, auto_attribs=True)
class PaymentAccountTable(TableDefinition):
    gino: Gino
    table: Table = no_init_attrib()
    name: str = no_init_attrib("payment_account")
    id: Column = no_init_attrib(Column("id", Integer, primary_key=True))
    account_type: Column = no_init_attrib(Column("account_type", Text))
    account_id: Column = no_init_attrib(Column("account_id", Integer))
    entity: Column = no_init_attrib(Column("entity", Text))
    old_account_id: Column = no_init_attrib(Column("old_account_id", Integer))
    upgraded_to_managed_account_at: Column = no_init_attrib(
        Column("upgraded_to_managed_account_at", DateTime(True))
    )
    is_verified_with_stripe: Column = no_init_attrib(
        Column("is_verified_with_stripe", Boolean)
    )
    transfers_enabled: Column = no_init_attrib(Column("transfers_enabled", Boolean))
    charges_enabled: Column = no_init_attrib(Column("charges_enabled", Boolean))
    statement_descriptor: Column = no_init_attrib(Column("statement_descriptor", Text))
    created_at: Column = no_init_attrib(Column("created_at", DateTime(True)))
    payout_disabled: Column = no_init_attrib(Column("payout_disabled", Boolean))
    resolve_outstanding_balance_frequency: Column = no_init_attrib(
        Column("resolve_outstanding_balance_frequency", Text)
    )
