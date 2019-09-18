from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, Text, DateTime
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class PayoutCardTable(TableDefinition):
    name: str = no_init_field("payout_cards")
    # id
    id: Column = no_init_field(Column("id", Integer, primary_key=True))
    # stripe_card_id
    stripe_card_id: Column = no_init_field(
        Column("stripe_card_id", Text, nullable=False)
    )
    # last4
    last4: Column = no_init_field(Column("last4", Text, nullable=False))
    # brand
    brand: Column = no_init_field(Column("brand", Text, nullable=False))
    # exp_month
    exp_month: Column = no_init_field(Column("exp_month", Integer, nullable=False))
    # exp_year
    exp_year: Column = no_init_field(Column("exp_year", Integer, nullable=False))
    # created_at
    created_at: Column = no_init_field(
        Column("created_at", DateTime(False), nullable=False)
    )
    # updated_at
    updated_at: Column = no_init_field(
        Column("updated_at", DateTime(False), nullable=False)
    )
    # fingerprint
    fingerprint: Column = no_init_field(Column("fingerprint", Text))


class _PayoutCardPartial(DBEntity):
    stripe_card_id: Optional[str]
    last4: Optional[str]
    brand: Optional[str]
    exp_month: Optional[int]
    exp_year: Optional[int]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    fingerprint: Optional[str]


class PayoutCard(_PayoutCardPartial):
    id: int
    stripe_card_id: str
    last4: str
    brand: str
    exp_month: int
    exp_year: int
    created_at: datetime
    updated_at: datetime
    fingerprint: str


class PayoutCardCreate(_PayoutCardPartial):
    id: int
    stripe_card_id: str
    last4: str
    brand: str
    exp_month: int
    exp_year: int
    created_at: datetime
    updated_at: datetime
    fingerprint: str
