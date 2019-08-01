from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gino import Gino, GinoConnection

from app.commons.utils.dataclass_extensions import no_init_field
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.types import MxTransactionType
from app.ledger.models.paymentdb.mx_transaction import MxTransactionTable


@dataclass
class MxTransactionRepository:
    _gino: Gino
    _table: MxTransactionTable = no_init_field()

    def __post_init__(self):
        self._table = MxTransactionTable(self._gino)

    async def insert_mx_transaction(
        self,
        mx_transaction_id: str,
        payment_account_id: str,
        amount: int,
        currency: str,
        ledger_id: str,
        idempotency_key: str,
        type: str,
        context: str,
        metadata: str,
    ) -> MxTransaction:
        data = {
            self._table.id: mx_transaction_id,
            self._table.payment_account_id: payment_account_id,
            self._table.amount: amount,
            self._table.currency: currency,
            self._table.ledger_id: ledger_id,
            self._table.idempotency_key: idempotency_key,
            self._table.type: type,
            self._table.context: context,
            self._table.metadata: metadata,
        }

        # FIXME: remove when payment db credential is setup
        if True:
            return self._to_mock_mx_transaction(
                mx_transaction_id=mx_transaction_id,
                payment_account_id=payment_account_id,
                amount=int(amount),
                currency=currency,
                ledger_id=ledger_id,
                idempotency_key=idempotency_key,
                type=MxTransactionType(type),
                context=context,
                metadata=metadata,
            )
        else:
            stmt = (
                self._table.table.insert()
                .values(data)
                .returning(*self._table.table.columns.values())
            )

            async with self._gino.acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_mx_transaction(row)

    def _to_mx_transaction(self, row: Any) -> MxTransaction:
        return MxTransaction(
            mx_transaction_id=row[self._table.id],
            payment_account_id=row[self._table.payment_account_id],
            amount=row[self._table.amount],
            currency=row[self._table.currency],
            ledger_id=row[self._table.ledger_id],
            idempotency_key=row[self._table.idempotency_key],
            type=MxTransactionType(row[self._table.type]),
            context=row[self._table.context],
            metadata=row[self._table.metadata],
            created_at=row[self._table.created_at],
            updated_at=row[self._table.updated_at],
        )

    # FIXME: remove when payment db credential is setup
    def _to_mock_mx_transaction(
        self,
        mx_transaction_id: str,
        payment_account_id: str,
        amount: int,
        currency: str,
        ledger_id: str,
        idempotency_key: str,
        type: MxTransactionType,
        context: str,
        metadata: str,
    ):
        return MxTransaction(
            mx_transaction_id=mx_transaction_id,
            payment_account_id=payment_account_id,
            amount=int(amount),
            currency=currency,
            ledger_id=ledger_id,
            idempotency_key=idempotency_key,
            type=MxTransactionType(type),
            context=context,
            metadata=metadata,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
