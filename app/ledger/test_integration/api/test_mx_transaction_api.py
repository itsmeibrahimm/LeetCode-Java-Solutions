import uuid
from datetime import datetime, timezone
from starlette.testclient import TestClient

from app.ledger.core.types import MxLedgerStateType
from app.ledger.test_integration.utils import prepare_transaction_post_request


class TestMxTransactionAPI:
    def test_create_transaction_and_close_ledger(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())

        # prepare a mx_transaction with routing_key as datetime(2019, 8, 1)
        first_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert first_response.status_code == 201
        mx_transaction: dict = first_response.json()
        assert mx_transaction["id"]
        assert mx_transaction["ledger_id"]
        mx_ledger_id = mx_transaction["ledger_id"]

        # prepare another mx_transaction with routing_key as datetime(2019, 8, 1)
        second_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert second_response.status_code == 201
        second_mx_transaction: dict = second_response.json()
        assert second_mx_transaction["id"]
        assert second_mx_transaction["ledger_id"]
        assert mx_ledger_id == second_mx_transaction["ledger_id"]

        # close this ledger and check status is processing
        close_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/process",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert close_ledger_response.status_code == 200
        mx_ledger: dict = close_ledger_response.json()
        assert mx_ledger["state"] == MxLedgerStateType.PROCESSING

        closed_ledger: dict = close_ledger_response.json()
        assert closed_ledger["id"] == mx_ledger_id
        assert closed_ledger["state"] == MxLedgerStateType.PROCESSING

        # prepare a mx_transaction with routing_key as datetime(2019, 8, 1), which will create a new ledger
        third_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert third_response.status_code == 201
        third_mx_transaction: dict = third_response.json()
        assert not third_mx_transaction["ledger_id"] == mx_ledger_id
        # todo: check start_time and end_time after we added GET scheduled_ledger API

    def test_create_multiple_transactions_route_to_correct_ledgers(
        self, client: TestClient
    ):
        payment_account_id = str(uuid.uuid4())

        # prepare a mx_transaction with routing_key as datetime(2019, 8, 1)
        first_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert first_response.status_code == 201
        mx_transaction: dict = first_response.json()
        assert mx_transaction["id"]
        assert mx_transaction["ledger_id"]
        first_mx_ledger_id = mx_transaction["ledger_id"]

        # prepare a mx_transaction with routing_key as datetime(2019, 8, 10)
        second_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id,
                routing_key=datetime(2019, 8, 10, tzinfo=timezone.utc),
            ),
        )
        assert second_response.status_code == 201
        second_mx_transaction: dict = second_response.json()
        assert second_mx_transaction["id"]
        assert second_mx_transaction["ledger_id"]
        second_ledger_id = second_mx_transaction["ledger_id"]
        assert not first_mx_ledger_id == second_ledger_id

        # close the second ledger
        close_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{second_ledger_id}/process",
            json={"mx_ledger_id": second_ledger_id},
        )
        assert close_ledger_response.status_code == 200
        closed_ledger: dict = close_ledger_response.json()
        assert closed_ledger["id"] == second_ledger_id
        assert closed_ledger["state"] == MxLedgerStateType.PROCESSING

        # prepare a new mx_transaction with routing_key as datetime(2019, 8, 1) and it routes to the first ledger
        thrid_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert thrid_response.status_code == 201
        thrid_mx_transaction: dict = thrid_response.json()
        assert thrid_mx_transaction["id"]
        assert thrid_mx_transaction["ledger_id"]
        assert first_mx_ledger_id == thrid_mx_transaction["ledger_id"]

        # prepare a new mx_transaction with routing_key as datetime(2019, 8, 10) and it creates a new ledger
        fourth_response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id,
                routing_key=datetime(2019, 8, 10, tzinfo=timezone.utc),
            ),
        )
        assert fourth_response.status_code == 201
        fourth_mx_transaction: dict = fourth_response.json()
        assert fourth_mx_transaction["id"]
        assert fourth_mx_transaction["ledger_id"]
        assert not first_mx_ledger_id == fourth_mx_transaction["ledger_id"]
