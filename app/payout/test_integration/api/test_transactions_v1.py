import time
from datetime import datetime, timezone
from typing import List
from uuid import uuid4

import pytz
from starlette.testclient import TestClient

from app.commons.types import CountryCode, Currency
import app.payout.api.account.v1.models as account_models
from app.payout.models import PayoutAccountTargetType

from app.payout.api.transaction.v1 import models
from app.payout.test_integration.api import (
    create_account_url,
    create_transaction_url,
    list_transactions_url,
    reverse_transaction_url,
)


class TestTransactionV1:
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

    def test_list_transactions(self, client: TestClient, payout_account: dict):
        # 0. find the existing number of transaction for the target_ids and type
        target_id_dasher_job_a = 2
        target_id_dasher_job_b = 3
        target_type_dasher_job = "dasher_job"
        target_ids = [target_id_dasher_job_a, target_id_dasher_job_b]
        target_ids_str = ",".join([str(target_id) for target_id in target_ids])
        tx_list_req_by_target_id_and_type = {
            "target_ids": target_ids_str,
            "target_type": target_type_dasher_job,
        }
        response = client.get(
            list_transactions_url(), params=tx_list_req_by_target_id_and_type
        )
        assert response.status_code == 200
        tx_retrieved: dict = response.json()
        exist_count = tx_retrieved["count"]

        # 1. prepare 5 transactions for the same payout account
        count_dasher_job_a = 5
        transactions_dasher_job_a = TestTransactionV1._prepare_transaction_list(
            client=client,
            payout_account=payout_account,
            count=count_dasher_job_a,
            target_id=target_id_dasher_job_a,
            target_type=target_type_dasher_job,
        )

        # 2. test list transactions by ids
        transaction_ids = ",".join(
            [str(transaction["id"]) for transaction in transactions_dasher_job_a]
        )
        tx_list_req = {"transaction_ids": transaction_ids}
        response = client.get(list_transactions_url(), params=tx_list_req)
        assert response.status_code == 200
        tx_retrieved_for_transaction_ids: dict = response.json()
        assert (
            tx_retrieved_for_transaction_ids["count"] == count_dasher_job_a
        ), f"retrieved {count_dasher_job_a} transaction"
        TestTransactionV1._validate_transaction_results(
            tx_retrieved_for_transaction_ids["transaction_list"],
            transactions_dasher_job_a,
        )

        # 3. prepare 3 transactions for different target_id and target_type
        count_dasher_job_b = 3
        transactions_dasher_job_b = TestTransactionV1._prepare_transaction_list(
            client=client,
            payout_account=payout_account,
            count=count_dasher_job_b,
            target_id=target_id_dasher_job_b,
            target_type=target_type_dasher_job,
        )
        expected_count = count_dasher_job_a + count_dasher_job_b
        expected_transactions = transactions_dasher_job_b + transactions_dasher_job_a
        response = client.get(
            list_transactions_url(), params=tx_list_req_by_target_id_and_type
        )
        assert response.status_code == 200
        tx_retrieved_for_target_ids_and_type: dict = response.json()
        expected_total_count = expected_count + exist_count
        assert (
            tx_retrieved_for_target_ids_and_type["count"] == expected_total_count
        ), f"retrieved {expected_count} transaction"
        TestTransactionV1._validate_transaction_results(
            tx_retrieved_for_target_ids_and_type["transaction_list"][:expected_count],
            expected_transactions,
        )

        # 4. insert 6 transaction for another payout account and list by payout account id
        count_for_account_b = 6
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
        transactions_for_account_b = TestTransactionV1._prepare_transaction_list(
            client=client, payout_account=account_created, count=count_for_account_b
        )
        tx_list_req_by_account_id = {"payout_account_id": account_created["id"]}
        response = client.get(list_transactions_url(), params=tx_list_req_by_account_id)
        assert response.status_code == 200
        tx_retrieved_for_account_id: dict = response.json()
        assert (
            tx_retrieved_for_account_id["count"] == count_for_account_b
        ), f"retrieved {count_for_account_b} transaction"
        TestTransactionV1._validate_transaction_results(
            tx_retrieved_for_account_id["transaction_list"], transactions_for_account_b
        )

        # 5. add another set of transactions for payout_account b
        # when we convert a utc time to timestamp, we truncate the fractional digits
        # so when the timestamp gets converted back to a datetime, it only has the sec
        # all millisec digits have been eliminated
        # therefore we need to sleep for seconds here to make set_b have different sec digit
        # with the previous set of transactions
        time.sleep(2)
        count_for_account_b_set_2 = 3
        transactions_for_account_b_set_b = TestTransactionV1._prepare_transaction_list(
            client=client,
            payout_account=account_created,
            count=count_for_account_b_set_2,
        )
        assert transactions_for_account_b_set_b[2]["created_at"]

        # 6. get unpaid transaction for payout account b with start_time
        start_time_str = transactions_for_account_b_set_b[2]["created_at"]
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%S.%f")
        start_time = start_time.replace(tzinfo=pytz.UTC)
        timestamp = int(
            (start_time - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds()
        )
        unpaid_tx_list_req_by_account_id_with_start_time = {
            "payout_account_id": account_created["id"],
            "unpaid": True,
            "ts_start": timestamp,
        }
        response = client.get(
            list_transactions_url(),
            params=unpaid_tx_list_req_by_account_id_with_start_time,
        )
        assert response.status_code == 200
        tx_retrieved_for_account_id_with_start_time: dict = response.json()
        TestTransactionV1._validate_transaction_results(
            tx_retrieved_for_account_id_with_start_time["transaction_list"],
            transactions_for_account_b_set_b,
        )

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

    @staticmethod
    def _prepare_transaction_list(
        client: TestClient,
        payout_account: dict,
        count: int = 5,
        target_id: int = 1,
        target_type: str = "dasher_job",
    ):
        transactions: List[dict] = []
        for i in range(0, count):
            test_idempotency_key = (
                f"test_create_then_list_transactions_{payout_account['id']}_{uuid4()}"
            )
            tx_creation_req = models.TransactionCreate(
                amount=10,
                payment_account_id=payout_account["id"],
                idempotency_key=test_idempotency_key,
                target_id=target_id,
                target_type=target_type,
                currency="usd",
            )
            response = client.post(
                create_transaction_url(), json=tx_creation_req.dict()
            )
            assert response.status_code == 201
            tx_created: dict = response.json()
            assert (
                tx_created["idempotency_key"] == test_idempotency_key
            ), "created tx with correct idempotency key"
            transactions.insert(0, tx_created)
        return transactions

    @staticmethod
    def _validate_transaction_results(
        actual_transaction_list: List[dict], expected_transaction_list: List[dict]
    ):
        assert len(actual_transaction_list) == len(
            expected_transaction_list
        ), f"retrieved {len(actual_transaction_list)}, expected {len(expected_transaction_list)} transactions"
        for i in range(0, len(actual_transaction_list)):
            actual_amount = actual_transaction_list[i]["amount"]
            expected_amount = expected_transaction_list[i]["amount"]
            actual_amount_paid = actual_transaction_list[i]["amount_paid"]
            expected_amount_paid = expected_transaction_list[i]["amount_paid"]
            actual_idempotency_key = actual_transaction_list[i]["idempotency_key"]
            expected_idempotency_key = expected_transaction_list[i]["idempotency_key"]
            assert (
                actual_amount == expected_amount
            ), f"transaction {i} actual amount {actual_amount} expected amount {expected_amount}"
            assert (
                actual_amount_paid == expected_amount_paid
            ), f"transaction {i} actual amount paid {actual_amount_paid} expected amount paid {expected_amount_paid}"
            assert actual_idempotency_key == expected_idempotency_key, (
                f"transaction {i} actual idempotency key {actual_idempotency_key} expected idempotency key "
                f"{expected_idempotency_key}"
            )
