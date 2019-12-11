from typing import List
from structlog.stdlib import BoundLogger
from app.commons.providers.dsj_client import DSJClient
from app.purchasecard.constants import (
    MarqetaResponseCodes,
    TransactionWebhookProcessType,
)
from app.purchasecard.repository.marqeta_transaction import MarqetaTransactionRepository
from app.purchasecard.core.webhook.models import (
    Transaction,
    TransactionProcessResult,
    TransactionProcessResults,
)
from doordash_python_stats.ddstats import doorstats_global


class WebhookProcessor:
    def __init__(
        self,
        logger: BoundLogger,
        repository: MarqetaTransactionRepository,
        dsj_client: DSJClient,
    ):
        self.logger = logger
        self.repository = repository
        self.dsj_client = dsj_client

    def is_transaction_successful(self, transaction: Transaction) -> bool:
        return transaction.response.code == MarqetaResponseCodes.SUCCESS.value

    def is_jit_failure(self, transaction: Transaction) -> bool:
        return transaction.gpa_order is not None

    def is_jit_failure_due_to_timeout(self, transaction: Transaction) -> bool:
        return (
            transaction.gpa_order is not None
            and transaction.gpa_order.funding.gateway_log.timed_out
        )

    def is_legit_jit_failure(self, transaction: Transaction) -> bool:
        return self.is_jit_failure(
            transaction
        ) and not self.is_jit_failure_due_to_timeout(transaction)

    def is_terminal_misconfiguration_failure(self, transaction: Transaction) -> bool:
        return transaction.response.code in (
            MarqetaResponseCodes.ECOMMERCE_TRANSACTION_NOT_ALLOWED.value,
            MarqetaResponseCodes.AUTH_RESTRICTION.value,
        )

    async def process_webhook_transactions(self, transactions: List[Transaction]):
        results = await self._process_webhook_transactions(transactions)
        return await self.dsj_client.post(
            f"/v1/payments/post_process_marqeta_webhook/", results.dict()
        )

    async def _process_webhook_transactions(
        self, transactions: List[Transaction]
    ) -> TransactionProcessResults:
        results = []
        for transaction in transactions:
            transaction_type: str = transaction.type
            if transaction_type != "authorization":
                continue
            transaction_token: str = transaction.token
            transaction_state: str = transaction.state
            doorstats_global.incr(
                "marqeta.transaction.payment.{}.{}".format(
                    transaction_type, transaction_state
                )
            )
            user_token: str = transaction.user_token
            if self.is_transaction_successful(transaction):
                updated_tx = await self.repository.update_marqeta_transaction_timeout_by_token(
                    transaction_token=transaction_token, timed_out=False
                )
                results.append(
                    TransactionProcessResult(
                        transaction_token=transaction_token,
                        process_type=TransactionWebhookProcessType.SUCCESS.value,
                        user_token=user_token,
                        delivery_id=updated_tx.delivery_id,
                        amount=updated_tx.amount,
                        card_acceptor=updated_tx.card_acceptor,
                    )
                )
            elif self.is_jit_failure_due_to_timeout(transaction):
                await self.repository.update_marqeta_transaction_timeout_by_token(
                    transaction_token=transaction_token, timed_out=True
                )
                results.append(
                    TransactionProcessResult(
                        transaction_token=transaction_token,
                        process_type=TransactionWebhookProcessType.TIMEOUT.value,
                        user_token=user_token,
                    )
                )
            elif self.is_legit_jit_failure(transaction):
                results.append(
                    TransactionProcessResult(
                        transaction_token=transaction_token,
                        process_type=TransactionWebhookProcessType.LEGIT_JIT_FAILURE.value,
                        user_token=user_token,
                    )
                )
            elif self.is_terminal_misconfiguration_failure(transaction):
                results.append(
                    TransactionProcessResult(
                        transaction_token=transaction_token,
                        process_type=TransactionWebhookProcessType.TERMINAL_FAILURE.value,
                        user_token=user_token,
                    )
                )
            else:
                results.append(
                    TransactionProcessResult(
                        transaction_token=transaction_token,
                        process_type=TransactionWebhookProcessType.OTHER.value,
                        user_token=user_token,
                    )
                )

        return TransactionProcessResults(processed_results=results)
