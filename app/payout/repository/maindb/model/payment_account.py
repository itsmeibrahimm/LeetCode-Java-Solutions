from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.sql.schema import SchemaItem
from typing_extensions import final

from app.commons.database.model import DBEntity, TableDefinition
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PaymentAccountTable(TableDefinition):
    """
    PaymentAccountTable

    Note: remember to update Entity classes below whenever schema changes
    """

    name: str = no_init_field("payment_account")
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('payment_account_id_seq'::regclass)"),
        )
    )
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
    statement_descriptor: Column = no_init_field(
        Column("statement_descriptor", Text, nullable=False)
    )
    created_at: Column = no_init_field(Column("created_at", DateTime(True)))
    payout_disabled: Column = no_init_field(Column("payout_disabled", Boolean))
    resolve_outstanding_balance_frequency: Column = no_init_field(
        Column("resolve_outstanding_balance_frequency", Text)
    )
    additional_schema_args: List[SchemaItem] = no_init_field(
        [
            CheckConstraint("account_id >= 0"),
            CheckConstraint("old_account_id >= 0"),
            Index(
                "payment_account_account_type_eef0b926_idx",
                "account_type",
                "account_id",
            ),
        ]
    )


class _PaymentAccountEntityBase(DBEntity):
    """
    Base Entity type for the table (schema fields are all optional)
    Concrete Entity should override the fields required by dropping `Optional`
    """

    id: Optional[int]
    account_type: Optional[str]
    account_id: Optional[int]
    entity: Optional[str]
    old_account_id: Optional[int]
    upgraded_to_managed_account_at: Optional[datetime]
    is_verified_with_stripe: Optional[bool]
    transfers_enabled: Optional[bool]
    charges_enabled: Optional[bool]
    statement_descriptor: Optional[str]
    created_at: Optional[datetime]
    payout_disabled: Optional[bool]
    resolve_outstanding_balance_frequency: Optional[str]


class PaymentAccountEntity(_PaymentAccountEntityBase):
    """
    NOT NULL columns
    """

    id: int
    statement_descriptor: str


class PaymentAccountCreate(_PaymentAccountEntityBase):
    id: DBEntity.NotAllowed = None
    statement_descriptor: str


class PaymentAccountUpdate(_PaymentAccountEntityBase):
    pass
