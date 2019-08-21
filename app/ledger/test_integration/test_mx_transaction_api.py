import uuid
from datetime import datetime

from starlette.testclient import TestClient

from app.commons.types import CurrencyType
from app.ledger.core.mx_transaction.types import (
    MxTransactionType,
    MxScheduledLedgerIntervalType,
)


class TestMxTransactionAPI:
    def test_create_mx_transaction_api(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        mx_transaction_request = {
            "payment_account_id": payment_account_id,
            "target_type": MxTransactionType.MERCHANT_DELIVERY.value,
            "amount": 3000,
            "currency": CurrencyType.USD.value,
            "idempotency_key": idempotency_key,
            "routing_key": datetime(2019, 8, 1).isoformat(),
            "interval_type": MxScheduledLedgerIntervalType.WEEKLY.value,
            "target_id": "optional_target_id",
            "context": "{}",
            "metadata": "{}",
            "legacy_transaction_id": "optional_legacy_transaction_id",
        }
        response = client.post(
            "/ledger/api/v1/mx_transactions", json=mx_transaction_request
        )
        assert response.status_code == 201
