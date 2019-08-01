from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from gino import GinoConnection

from app.commons.database.model import Database
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.types import MxTransactionType
from app.ledger.models.paymentdb import mx_transactions


@dataclass
class MxTransactionRepository:
    _db: Database

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
            mx_transactions.id: mx_transaction_id,
            mx_transactions.payment_account_id: payment_account_id,
            mx_transactions.amount: amount,
            mx_transactions.currency: currency,
            mx_transactions.ledger_id: ledger_id,
            mx_transactions.idempotency_key: idempotency_key,
            mx_transactions.type: type,
            mx_transactions.context: context,
            mx_transactions.metadata: metadata,
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
                mx_transactions.insert()
                .values(data)
                .returning(*mx_transactions.table.columns.values())
            )

            async with self._db.master().acquire() as connection:  # type: GinoConnection
                row = await connection.first(stmt)
            return self._to_mx_transaction(row)

    def _to_mx_transaction(self, row: Any) -> MxTransaction:
        return MxTransaction(
            mx_transaction_id=row[mx_transactions.id],
            payment_account_id=row[mx_transactions.payment_account_id],
            amount=row[mx_transactions.amount],
            currency=row[mx_transactions.currency],
            ledger_id=row[mx_transactions.ledger_id],
            idempotency_key=row[mx_transactions.idempotency_key],
            type=MxTransactionType(row[mx_transactions.type]),
            context=row[mx_transactions.context],
            metadata=row[mx_transactions.metadata],
            created_at=row[mx_transactions.created_at],
            updated_at=row[mx_transactions.updated_at],
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
