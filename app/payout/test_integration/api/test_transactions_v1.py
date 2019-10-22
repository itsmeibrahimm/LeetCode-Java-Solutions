from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from app.commons.types import CountryCode, Currency
from app.payout.api.account.v1 import models as account_models
from app.payout.models import PayoutAccountTargetType

from app.payout.api.transaction.v1 import models
from app.payout.test_integration.api import (
    create_account_url,
    create_transaction_url,
    list_transactions_url,
    reverse_transaction_url,
)


class TestTransactionV1:
    @pytest.fixture
    def payout_account(self, client: TestClient) -> dict:
        create_payment_account_req = account_models.CreatePayoutAccount(
            target_id=1,
            target_type=PayoutAccountTargetType.DASHER,
            country=CountryCode.US,
            currency=Currency.USD,
            statement_descriptor="test_statement_descriptor",
        )
        response = client.post(
            create_account_url(), json=create_payment_account_req.dict()
        )
        assert response.status_code == 201
        account_created: dict = response.json()
        assert (
            account_created["statement_descriptor"]
            == create_payment_account_req.statement_descriptor
        ), "created payout account's statement_descriptor matches with expected"
        return account_created

    @pytest.fixture
    def new_transaction(self, client: TestClient, payout_account: dict) -> dict:
        test_idempotency_key = (
            f"test_create_then_list_transactions_{payout_account['id']}_{uuid4()}"
        )
        tx_creation_req = models.TransactionCreate(
            amount=10,
            payment_account_id=payout_account["id"],
            idempotency_key=test_idempotency_key,
            target_id=1,
            target_type="dasher_job",
            currency="usd",
        )
        response = client.post(create_transaction_url(), json=tx_creation_req.dict())
        assert response.status_code == 201
        tx_created: dict = response.json()
        assert (
            tx_created["idempotency_key"] == test_idempotency_key
        ), "created tx with correct idempotency key"
        return tx_created

    def test_create_then_list_transactions(
        self, client: TestClient, new_transaction: dict
    ):
        idempotency_key = new_transaction["idempotency_key"]

        # query param is comma-separated list and contains dupe ids
        tx_list_req = {
            "transaction_ids": f"{new_transaction['id']},{new_transaction['id']}"
        }
        response = client.get(list_transactions_url(), params=tx_list_req)
        assert response.status_code == 200
        tx_retrieved: dict = response.json()
        assert tx_retrieved["count"] == 1, "retrieved 1 transaction"
        assert (
            tx_retrieved["transaction_list"][0]["idempotency_key"] == idempotency_key
        ), "retrieved the transaction"

    def test_create_then_reverse_transactions(
        self, client: TestClient, new_transaction: dict
    ):
        tx_reverse_req = models.ReverseTransaction(reverse_reason=None)
        response = client.post(
            reverse_transaction_url(new_transaction["id"]), json=tx_reverse_req.dict()
        )
        assert response.status_code == 200
        tx_reversed: dict = response.json()
        assert tx_reversed["id"] != new_transaction["id"], "this is a new transaction"
        assert tx_reversed["amount"] == -new_transaction["amount"], "amount is correct"
        assert (
            tx_reversed["payout_account_id"] == new_transaction["payout_account_id"]
        ), "account is correct"
