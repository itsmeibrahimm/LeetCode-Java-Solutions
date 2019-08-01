from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from gino import GinoConnection

from app.commons.database.model import Database
from app.payin.core.payer.model import Payer, PaymentGatewayProviderCustomer
from app.payin.core.payer.types import PayerType
from app.payin.models.paymentdb import payers


@dataclass
class PayerRepository:
    _db: Database

    async def insert_payer(
        self,
        payer_id: str,
        payer_type: str,
        legacy_stripe_customer_id: str,
        country: str,
        account_balance: Optional[int] = None,
        description: Optional[str] = None,
        dd_payer_id: Optional[str] = None,
    ) -> Payer:
        # FIXME: remove when payment db credential is setup
        if self:
            return self._to_mock_payer(
                payer_id=payer_id,
                payer_type=payer_type,
                dd_payer_id=dd_payer_id,
                legacy_stripe_customer_id=legacy_stripe_customer_id,
                country=country,
                account_balance=account_balance,
                description=description,
            )
        else:
            data = {
                payers.id: payer_id,
                payers.payer_type: payer_type,
                payers.legacy_stripe_customer_id: legacy_stripe_customer_id,
                payers.country: country,
            }
            if account_balance:
                data.update({payers.account_balance: account_balance})
            if description:
                data.update({payers.description: description})
            if dd_payer_id:
                data.update({payers.dd_payer_id: dd_payer_id})
            stmt = (
                payers.table.insert()
                .values(data)
                .returning(*payers.table.columns.values())
            )

            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_payer(row)

    async def get_payer_by_id(self, payer_id: str) -> Optional[Payer]:
        stmt = payers.table.select().where(payers.id == payer_id)
        # FIXME: remove when payment db credential is setup
        if True:
            return self._to_mock_payer(
                payer_id=payer_id,
                payer_type="drive",
                dd_payer_id="1234",
                legacy_stripe_customer_id="mock_legacy_stripe_customer_id",
                country="mock_country",
                account_balance=0,
                description="mock_description",
            )
        else:
            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_payer(row) if row else None

    async def get_payer_by_stripe_customer_id(
        self, stripe_customer_id: str
    ) -> Optional[Payer]:
        stmt = payers.table.select().where(
            payers.legacy_stripe_customer_id == stripe_customer_id
        )
        # FIXME: remove when payment db credential is setup
        if True:
            return self._to_mock_payer(
                payer_id="mock_payer_id",
                payer_type="drive",
                dd_payer_id="1234",
                legacy_stripe_customer_id=stripe_customer_id,
                country="mock_US",
                account_balance=0,
                description="mock_description",
            )
        else:
            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_payer(row) if row else None

    def _to_payer(self, row: Any) -> Payer:
        return Payer(
            payer_id=row[payers.id],
            payer_type=PayerType(row[payers.payer_type]),
            dd_payer_id=row[payers.dd_payer_id],
            payment_gateway_provider_customers=[
                PaymentGatewayProviderCustomer(
                    payment_provider="stripe",
                    payment_provider_customer_id=row[payers.legacy_stripe_customer_id],
                )
            ],
            country=row[payers.country],
            # account_balance=row[payers.account_balance],
            description=row[payers.description],
            created_at=row[payers.created_at],
            updated_at=row[payers.updated_at],
        )

    # FIXME: remove when payment db credential is setup
    def _to_mock_payer(
        self,
        payer_id: str,
        payer_type: str,
        legacy_stripe_customer_id: str,
        country: str,
        dd_payer_id: Optional[str],
        account_balance: Optional[int],
        description: Optional[str],
    ):
        return Payer(
            payer_id=payer_id,
            payer_type=PayerType(payer_type),
            dd_payer_id=dd_payer_id,
            payment_gateway_provider_customers=[
                PaymentGatewayProviderCustomer(
                    payment_provider="stripe",
                    payment_provider_customer_id=legacy_stripe_customer_id,
                )
            ],
            country=country,
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
