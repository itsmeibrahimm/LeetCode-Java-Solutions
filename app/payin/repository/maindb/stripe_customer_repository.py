from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from gino import GinoConnection

from app.commons.database.model import Database
from app.payin.core.payer.model import StripeCustomer
from app.payin.models.maindb import stripe_customers


@dataclass
class StripeCustomerRepository:
    _maindb: Database

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
            stripe_customers.stripe_id: stripe_customer_id,
            stripe_customers.country_shortname: country,
            stripe_customers.owner_type: owner_type,
            stripe_customers.owner_id: owner_id,
            stripe_customers.default_card: default_card,
            stripe_customers.default_source: default_source,
        }

        stmt = (
            stripe_customers.table.insert()
            .values(data)
            .returning(*stripe_customers.table.columns.values())
        )

        async with self._maindb.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)

        return self._to_stripe_customer(row)

    async def update_stripe_customer(
        self, primary_id: int, default_source: str
    ) -> StripeCustomer:
        data = {
            stripe_customers.id: primary_id,
            stripe_customers.default_source: default_source,
        }
        stmt = (
            stripe_customers.table.update()
            .values(data)
            .returning(*stripe_customers.table.columns.values())
        )
        async with self._maindb.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row)

    async def update_stripe_customer_by_stripe_id(
        self, stripe_customer_id: str, default_source: str
    ) -> StripeCustomer:
        data = {
            stripe_customers.stripe_id: stripe_customer_id,
            stripe_customers.default_source: default_source,
        }
        stmt = (
            stripe_customers.table.update()
            .values(data)
            .returning(*stripe_customers.table.columns.values())
        )
        async with self._maindb.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row)

    async def get_stripe_customer_by_id(
        self, primary_id: int
    ) -> Optional[StripeCustomer]:
        stmt = stripe_customers.table.select().where(stripe_customers.id == primary_id)
        async with self._maindb.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row) if row else None

    async def get_stripe_customer_by_stripe_customer_id(
        self, stripe_customer_id: str
    ) -> Optional[StripeCustomer]:
        stmt = stripe_customers.table.select().where(
            stripe_customers.stripe_id == stripe_customer_id
        )
        async with self._maindb.master().acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)
        return self._to_stripe_customer(row) if row else None

    def _to_stripe_customer(self, row: Any) -> StripeCustomer:
        return StripeCustomer(
            id=row[stripe_customers.id],
            stripe_id=row[stripe_customers.stripe_id],
            country_shortname=row[stripe_customers.country_shortname],
            owner_type=row[stripe_customers.owner_type],
            owner_id=row[stripe_customers.owner_id],
            default_card=row[stripe_customers.default_card],
            default_source=row[stripe_customers.default_source],
        )
