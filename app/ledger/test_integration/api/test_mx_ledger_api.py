from starlette.testclient import TestClient
from app.commons.types import CurrencyType

import uuid

from app.ledger.core.types import MxLedgerType


class TestMxLedgerAPI:
    def test_create_one_off_mx_ledger_api(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())
        one_off_mx_ledger_request = {
            "payment_account_id": payment_account_id,
            "currency": CurrencyType.USD.value,
            "balance": 2000,
            "type": MxLedgerType.MICRO_DEPOSIT.value,
        }
        response = client.post(
            "/ledger/api/v1/mx_ledgers", json=one_off_mx_ledger_request
        )
        assert response.status_code == 201
