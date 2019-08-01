from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from gino import GinoConnection

from app.commons.database.model import Database
from app.payin.core.payer.model import PgpCustomer
from app.payin.models.paymentdb import pgp_customers


@dataclass
class PgpCustomerRepository:
    _db: Database

    async def insert_pgp_customer(
        self,
        id: str,
        pgp_code: str,
        pgp_resource_id: str,
        payer_id: str,
        account_balance: int,
        currency: Optional[str] = None,
        default_payment_method: Optional[str] = None,
        legacy_default_card: Optional[str] = None,
        legacy_default_source: Optional[str] = None,
    ) -> PgpCustomer:
        if True:
            return self._to_mock_pgp_customer(
                id,
                pgp_code,
                pgp_resource_id,
                payer_id,
                currency,
                default_payment_method,
                legacy_default_card,
                legacy_default_source,
            )
        else:
            data = {
                pgp_customers.id: id,
                pgp_customers.pgp_code: pgp_code,
                pgp_customers.pgp_resource_id: pgp_resource_id,
                pgp_customers.payer_id: payer_id,
                pgp_customers.account_balance: account_balance,
                pgp_customers.default_payment_method: default_payment_method,
                pgp_customers.legacy_default_card: legacy_default_card,
                pgp_customers.legacy_default_source: legacy_default_source,
            }
            if currency:
                data.update({pgp_customers.currency: currency})
            stmt = (
                pgp_customers.table.insert()
                .values(data)
                .returning(*pgp_customers.table.columns.values())
            )

            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)

            return self._to_pgp_customer(row)

    async def update_pgp_customer_default_payment_method(
        self, pgp_customer_id: str, default_payment_method_id: str
    ) -> PgpCustomer:
        if True:
            return self._to_mock_pgp_customer(
                id=pgp_customer_id,
                pgp_code="stripe",
                pgp_resource_id="mock_cus_abc",
                payer_id="mock_payer_id",
                currency="US",
                default_payment_method=default_payment_method_id,
                legacy_default_source=default_payment_method_id,
            )
        else:
            data = {
                pgp_customers.id: pgp_customer_id,
                pgp_customers.default_source: default_payment_method_id,
                pgp_customers.default_payment_method: default_payment_method_id,
            }
            stmt = (
                pgp_customers.table.update()
                .values(data)
                .returning(*pgp_customers.table.columns.values())
            )
            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_pgp_customer(row)

    async def get_pgp_customer_by_payer_id_and_pgp_code(
        self, payer_id: str, pgp_code: str
    ) -> Optional[PgpCustomer]:
        # FIXME: remove when payment db credential is setup
        if True:
            return self._to_mock_pgp_customer(
                id="mock_pgcu_abc",
                pgp_code=pgp_code,
                pgp_resource_id="mock_cus_abc",
                payer_id=payer_id,
                currency="US",
                default_payment_method="mock_default_payment_method",
                legacy_default_card="mock_legacy_default_card",
                legacy_default_source="mock_legacy_default_source",
            )
        else:
            stmt = pgp_customers.table.select().where(
                pgp_customers.payer_id == payer_id, pgp_customers.pgp_code == pgp_code
            )
            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_payer(row) if row else None

    def _to_pgp_customer(self, row: Any) -> PgpCustomer:
        return PgpCustomer(
            id=row[pgp_customers.id],
            legacy_id=row[pgp_customers.legacy_id],
            pgp_code=row[pgp_customers.pgp_code],
            pgp_resource_id=row[pgp_customers.pgp_resource_id],
            payer_id=row[pgp_customers.payer_id],
            currency=row[pgp_customers.currency],
            default_payment_method=row[pgp_customers.default_payment_method],
            legacy_default_card=row[pgp_customers.legacy_default_card],
            legacy_default_source=row[pgp_customers.legacy_default_source],
            created_at=row[pgp_customers.created_at],
            updated_at=row[pgp_customers.updated_at],
        )

    # FIXME: remove when payment db credential is setup
    def _to_mock_pgp_customer(
        self,
        id: str,
        pgp_code: str,
        pgp_resource_id: str,
        payer_id: str,
        currency: Optional[str],
        default_payment_method: Optional[str] = None,
        legacy_default_card: Optional[str] = None,
        legacy_default_source: Optional[str] = None,
    ) -> PgpCustomer:
        return PgpCustomer(
            id=id,
            pgp_code=pgp_code,
            legacy_id=123,
            pgp_resource_id=pgp_resource_id,
            payer_id=payer_id,
            currency=currency,
            default_payment_method=default_payment_method,
            legacy_default_card=legacy_default_card,
            legacy_default_source=legacy_default_source,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
