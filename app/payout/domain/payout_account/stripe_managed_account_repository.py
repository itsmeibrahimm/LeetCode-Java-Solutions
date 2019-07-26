from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from gino import Gino, GinoConnection

from app.commons.utils.dataclass_extensions import no_init_field
from app.payout.database.maindb.stripe_managed_account import StripeManagedAccountTable
from app.payout.domain.payout_account.models import StripeManagedAccount


@dataclass
class StripeManagedAccountRepository:
    _gino: Gino
    _table: StripeManagedAccountTable = no_init_field()

    def __post_init__(self):
        self._table = StripeManagedAccountTable(self._gino)

    async def get_stripe_managed_account_by_id(
        self, stripe_managed_account_id: int
    ) -> Optional[StripeManagedAccount]:
        stmt = self._table.table.select().where(
            self._table.id == stripe_managed_account_id
        )
        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)

        return self._deserialize_to_stripe_managed_account(row) if row else None

    async def create_stripe_managed_account(
        self, to_create: StripeManagedAccount
    ) -> StripeManagedAccount:
        data = {
            self._table.bank_account_last_updated_at: to_create.bank_account_last_updated_at,
            self._table.country_short_name: to_create.country_short_name,
            self._table.default_bank_last_four: to_create.default_bank_last_four,
            self._table.default_bank_name: to_create.default_bank_name,
            self._table.fingerprint: to_create.fingerprint,
            self._table.stripe_id: to_create.stripe_id,
            self._table.stripe_last_updated_at: to_create.stripe_last_updated_at,
            self._table.verification_disabled_reason: to_create.verification_disabled_reason,
            self._table.verification_due_by: to_create.verification_due_by,
            self._table.verification_fields_needed: to_create.verification_fields_needed,
        }

        stmt = (
            self._table.table.insert()
            .values(data)
            .returning(*self._table.table.columns.values())
        )

        async with self._gino.acquire() as connection:  # type: GinoConnection
            row = await connection.first(stmt)

        return self._deserialize_to_stripe_managed_account(row)

    def _deserialize_to_stripe_managed_account(self, row: Any) -> StripeManagedAccount:
        return StripeManagedAccount(
            id=row[self._table.id],
            bank_account_last_updated_at=row[self._table.bank_account_last_updated_at],
            country_short_name=row[self._table.country_short_name],
            default_bank_last_four=row[self._table.default_bank_last_four],
            default_bank_name=row[self._table.default_bank_name],
            fingerprint=row[self._table.fingerprint],
            stripe_id=row[self._table.stripe_id],
            verification_disabled_reason=row[self._table.stripe_id],
            verification_due_by=row[self._table.verification_due_by],
            verification_fields_needed=row[self._table.verification_fields_needed],
        )
