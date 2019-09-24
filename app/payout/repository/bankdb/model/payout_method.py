from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Integer, text, Text, DateTime, Boolean
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.providers.stripe.stripe_models import StripeCard
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PayoutMethodTable(TableDefinition):
    name: str = no_init_field("payout_methods")
    # id
    id: Column = no_init_field(
        Column(
            "id",
            Integer,
            primary_key=True,
            server_default=text("nextval('payout_methods_id_seq'::regclass)"),
        )
    )
    # type
    type: Column = no_init_field(Column("type", Text, nullable=False))
    # currency
    currency: Column = no_init_field(Column("currency", Text, nullable=False))
    # country
    country: Column = no_init_field(Column("country", Text, nullable=False))
    # payment_account_id
    payment_account_id: Column = no_init_field(
        Column("payment_account_id", Integer, nullable=False)
    )
    # created_at
    created_at: Column = no_init_field(
        Column("created_at", DateTime(False), nullable=False)
    )
    # updated_at
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(False), nullable=False)
    )
    # is_default
    is_default: Column = no_init_field(Column("is_default", Boolean))
    # token
    token: Column = no_init_field(Column("token", Text, nullable=False))
    # deleted_at
    deleted_at: Column = no_init_field(Column("deleted_at", DateTime(False)))


class _PayoutMethodPartial(DBEntity):
    type: Optional[str]
    currency: Optional[str]
    country: Optional[str]
    payment_account_id: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    is_default: Optional[bool]
    token: Optional[UUID]
    deleted_at: Optional[datetime]


class PayoutMethod(_PayoutMethodPartial):
    id: int
    type: str
    currency: str
    country: str
    payment_account_id: int
    created_at: datetime
    updated_at: datetime
    token: UUID


class PayoutMethodCreate(_PayoutMethodPartial):
    type: str
    currency: str
    country: str
    payment_account_id: int
    is_default: bool
    token: UUID


class PayoutMethodUpdate(_PayoutMethodPartial):
    deleted_at: datetime


class PayoutMethodMiscellaneousCreate(DBEntity):
    payout_account_id: int
    payout_method_type: str
    card: StripeCard
