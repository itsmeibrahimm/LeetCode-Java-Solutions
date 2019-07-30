from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from gino import Gino, GinoConnection

from app.commons.utils.dataclass_extensions import no_init_field
from app.payin.core.payer.model import StripeCustomer
from app.payin.models.maindb.stripe_customer import StripeCustomerTable


@dataclass
class StripeCustomerRepository:
    _gino: Gino
    _table: StripeCustomerTable = no_init_field()

    def __post_init__(self):
        self._table = StripeCustomerTable(self._gino)

    async def insert_stripe_customer(
        self,
        stripe_customer_id: str,
        country: str,
        owner_type: str,
        owner_id: int,
        default_card: str,
        default_source: str,
    ) -> StripeCustomer:
        data = {
            self._table.stripe_id: stripe_customer_id,
            self._table.country_shortname: country,
            self._table.owner_type: owner_type,
            self._table.owner_id: owner_id,
            self._table.default_card: default_card,
            self._table.default_source: default_source,
        }

        stmt = (
            self._table.table.insert()
            .values(data)
            .returning(*self._table.table.columns.values())
        )

        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)

        return self._to_stripe_customer(row)

    async def update_stripe_customer(
        self, primary_id: int, default_source: str
    ) -> StripeCustomer:
        data = {self._table.id: primary_id, self._table.default_source: default_source}
        stmt = (
            self._table.table.update()
            .values(data)
            .returning(*self._table.table.columns.values())
        )
        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row)

    async def update_stripe_customer_by_stripe_id(
        self, stripe_customer_id: str, default_source: str
    ) -> StripeCustomer:
        data = {
            self._table.stripe_id: stripe_customer_id,
            self._table.default_source: default_source,
        }
        stmt = (
            self._table.table.update()
            .values(data)
            .returning(*self._table.table.columns.values())
        )
        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row)

    async def get_stripe_customer_by_id(
        self, primary_id: int
    ) -> Optional[StripeCustomer]:
        stmt = self._table.table.select().where(self._table.id == primary_id)
        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row) if row else None

    async def get_stripe_customer_by_stripe_customer_id(
        self, stripe_customer_id: str
    ) -> Optional[StripeCustomer]:
        stmt = self._table.table.select().where(
            self._table.stripe_id == stripe_customer_id
        )
        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row) if row else None

    def _to_stripe_customer(self, row: Any) -> StripeCustomer:
        return StripeCustomer(
            id=row[self._table.id],
            stripe_id=row[self._table.stripe_id],
            country_shortname=row[self._table.country_shortname],
            owner_type=row[self._table.owner_type],
            owner_id=row[self._table.owner_id],
            default_card=row[self._table.default_card],
            default_source=row[self._table.default_source],
        )
