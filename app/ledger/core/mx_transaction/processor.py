import logging
import uuid
from datetime import datetime

from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.types import MxTransactionType
from app.ledger.repository.mx_transaction_repository import (
    InsertMxTransactionInput,
    InsertMxTransactionOutput,
)

logger = logging.getLogger(__name__)


async def create_mx_transaction(
    payment_account_id: str,
    target_type: MxTransactionType,
    amount: int,
    currency: str,
    idempotency_key: str,
    routing_key: datetime,
    target_id: str,
    context: str,
    metadata: str,
) -> MxTransaction:
    # FIXME: should be move into app_context.
    from app.ledger.ledger import mx_transaction_repository as tr

    # Step 1: Use payment_account_repo.get_or_create_ledger to find the current open ledger
    ledger_id = generate_object_uuid(ResourceUuidPrefix.MX_TRANSACTION)

    # step 2: create mx_transaction object
    mx_transaction_to_insert = InsertMxTransactionInput(
        id=uuid.uuid4(),
        payment_account_id=payment_account_id,
        amount=int(amount),
        currency=currency,
        ledger_id=ledger_id,
        idempotency_key=idempotency_key,
        target_type=type,
        routing_key=routing_key,
        context=context,
        metadata=metadata,
    )

    mx_transaction: InsertMxTransactionOutput = await tr.insert_mx_transaction(
        mx_transaction_to_insert
    )

    # step 3: Update ledger's balance

    return MxTransaction(
        mx_transaction_id=mx_transaction.id,
        payment_account_id=payment_account_id,
        amount=amount,
        currency=currency,
        ledger_id=ledger_id,
        idempotency_key=idempotency_key,
        target_type=target_type,
        routing_key=routing_key,
        target_id=target_id,
        context=context,
        metadata=metadata,
        created_at=mx_transaction.created_at,
        updated_at=mx_transaction.updated_at,
        legacy_transaction_id="optional_legacy_txn_id",
    )
