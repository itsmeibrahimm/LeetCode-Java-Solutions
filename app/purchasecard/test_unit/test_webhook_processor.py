import pytest
from datetime import datetime
from asynctest import MagicMock, CoroutineMock
from app.purchasecard.constants import (
    MarqetaResponseCodes,
    TransactionWebhookProcessType,
)
from app.purchasecard.core.webhook.models import (
    Response,
    GatewayLog,
    Funding,
    GpaOrder,
    Transaction,
)
from app.purchasecard.models.maindb.marqeta_transaction import (
    MarqetaTransactionDBEntity,
)
from app.purchasecard.core.webhook.processor import WebhookProcessor


class TestWebhookProcessor:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(self):
        marqeta_transaction_repo = MagicMock()
        marqeta_transaction_repo.update_marqeta_transaction_timeout_by_token = CoroutineMock(
            return_value=MarqetaTransactionDBEntity(
                token="token",
                id=1,
                amount=2,
                delivery_id=3,
                card_acceptor="acceptor",
                swiped_at=datetime.now(),
            )
        )
        self.webhook_processor = WebhookProcessor(
            logger=MagicMock(),
            repository=marqeta_transaction_repo,
            dsj_client=MagicMock(),
        )

    @pytest.fixture
    def fake_transactions(self):
        token = "token"
        type = "authorization"
        state = "state"
        user_token = "user_token"
        r1 = Response(code=MarqetaResponseCodes.SUCCESS.value)
        gpa_order1 = GpaOrder(funding=Funding(gateway_log=GatewayLog(timed_out=False)))
        t1 = Transaction(
            token=token,
            type=type,
            state=state,
            response=r1,
            user_token=user_token,
            gpa_order=gpa_order1,
        )

        gpa_order2 = GpaOrder(funding=Funding(gateway_log=GatewayLog(timed_out=True)))
        r2 = Response(code=MarqetaResponseCodes.ACCOUNT_LOAD_FAILED.value)
        t2 = Transaction(
            token=token,
            type=type,
            state=state,
            response=r2,
            user_token=user_token,
            gpa_order=gpa_order2,
        )

        gpa_order3 = GpaOrder(funding=Funding(gateway_log=GatewayLog(timed_out=False)))
        r3 = Response(code=MarqetaResponseCodes.ACCOUNT_LOAD_FAILED.value)
        t3 = Transaction(
            token=token,
            type=type,
            state=state,
            response=r3,
            user_token=user_token,
            gpa_order=gpa_order3,
        )

        r4 = Response(code=MarqetaResponseCodes.ECOMMERCE_TRANSACTION_NOT_ALLOWED.value)
        t4 = Transaction(
            token=token, type=type, state=state, response=r4, user_token=user_token
        )

        r5 = Response(code="other")
        t5 = Transaction(
            token=token, type=type, state=state, response=r5, user_token=user_token
        )
        return [t1, t2, t3, t4, t5]

    async def test_process_webhook_transactions(self, fake_transactions):
        results = await self.webhook_processor._process_webhook_transactions(
            fake_transactions
        )
        assert len(results.processed_results) == 5

        assert (
            results.processed_results[0].process_type
            == TransactionWebhookProcessType.SUCCESS.value
        )
        assert results.processed_results[0].amount == 2
        assert results.processed_results[0].delivery_id == 3
        assert results.processed_results[0].card_acceptor == "acceptor"

        assert (
            results.processed_results[1].process_type
            == TransactionWebhookProcessType.TIMEOUT.value
        )

        assert (
            results.processed_results[2].process_type
            == TransactionWebhookProcessType.LEGIT_JIT_FAILURE.value
        )

        assert (
            results.processed_results[3].process_type
            == TransactionWebhookProcessType.TERMINAL_FAILURE.value
        )

        assert (
            results.processed_results[4].process_type
            == TransactionWebhookProcessType.OTHER.value
        )
