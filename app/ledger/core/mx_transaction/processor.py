import logging

from app.commons.utils.uuid import generate_object_uuid, ResourceUuidPrefix
from app.ledger.core.mx_transaction.model import MxTransaction
from app.ledger.core.mx_transaction.types import MxTransactionType

logger = logging.getLogger(__name__)


async def create_mx_transaction(
    payment_account_id: str,
    type: MxTransactionType,
    amount: int,
    currency: str,
    idempotency_key: str,
    context: str,
    metadata: str,
) -> MxTransaction:
    # FIXME: should be move into app_context.
    from app.ledger.ledger import ledger_repositories as lr

    # Step 1: Use payment_account_repo.get_or_create_ledger to find the current open ledger
    ledger_id = generate_object_uuid(ResourceUuidPrefix.MX_TRANSACTION)

    # step 2: create mx_transaction object
    mx_transaction: MxTransaction = await lr.mx_transaction_repo.insert_mx_transaction(
        mx_transaction_id=generate_object_uuid(ResourceUuidPrefix.MX_TRANSACTION),
        payment_account_id=payment_account_id,
        amount=int(amount),
        currency=currency,
        ledger_id=ledger_id,
        idempotency_key=idempotency_key,
        type=type.value,
        context=context,
        metadata=metadata,
    )

    # step 3: Update ledger's balance

    return MxTransaction(
        mx_transaction_id=mx_transaction.mx_transaction_id,
        payment_account_id=payment_account_id,
        amount=amount,
        currency=currency,
        ledger_id=ledger_id,
        idempotency_key=idempotency_key,
        type=type,
        context=context,
        metadata=metadata,
        created_at=mx_transaction.created_at,
        updated_at=mx_transaction.updated_at,
    )
