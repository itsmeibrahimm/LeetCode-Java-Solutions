import uuid

from starlette.testclient import TestClient

from app.commons.types import Currency
from app.ledger.core.exceptions import LedgerErrorCode
from app.ledger.core.types import MxLedgerType, MxLedgerStateType
from app.ledger.test_integration.utils import prepare_transaction_post_request


class TestMxLedgerAPI:
    def test_process_ledger_not_exist_raise_error(self, client: TestClient):
        mx_ledger_id = str(uuid.uuid4())
        process_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/process",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert process_ledger_response.status_code == 404
        error: dict = process_ledger_response.json()
        assert error["error_code"] == LedgerErrorCode.MX_LEDGER_NOT_FOUND
        assert not error["retryable"]

    def test_process_and_submit_ledger_success(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())
        # prepare a mx_transaction and insert
        response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert response.status_code == 201
        mx_transaction: dict = response.json()
        assert mx_transaction["id"]
        assert mx_transaction["ledger_id"]
        mx_ledger_id = mx_transaction["ledger_id"]

        # post process ledger request
        process_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/process",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert process_ledger_response.status_code == 200
        mx_ledger: dict = process_ledger_response.json()
        assert mx_ledger["state"] == MxLedgerStateType.PROCESSING

        # post submit ledger request
        submit_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/submit",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert submit_ledger_response.status_code == 200
        submitted_mx_ledger: dict = submit_ledger_response.json()
        assert submitted_mx_ledger["state"] == MxLedgerStateType.SUBMITTED

    def test_process_ledger_multiple_times_raise_error(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())
        # prepare a mx_transaction and insert
        response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert response.status_code == 201
        mx_transaction: dict = response.json()
        assert mx_transaction["id"]
        assert mx_transaction["ledger_id"]
        mx_ledger_id = mx_transaction["ledger_id"]

        # post process ledger request
        process_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/process",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert process_ledger_response.status_code == 200
        mx_ledger: dict = process_ledger_response.json()
        assert mx_ledger["state"] == MxLedgerStateType.PROCESSING

        # process same ledger again and raise error
        process_same_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/process",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert process_same_ledger_response.status_code == 400
        error: dict = process_same_ledger_response.json()
        assert error["error_code"] == LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE
        assert not error["retryable"]

    def test_submit_ledger_not_exist_raise_error(self, client: TestClient):
        # post submit ledger request
        mx_ledger_id = str(uuid.uuid4())
        submit_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/submit",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert submit_ledger_response.status_code == 404
        error: dict = submit_ledger_response.json()
        assert error["error_code"] == LedgerErrorCode.MX_LEDGER_NOT_FOUND
        assert not error["retryable"]

    def test_submit_ledger_multiple_times_raise_error(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())
        # prepare a mx_transaction and insert
        response = client.post(
            "/ledger/api/v1/mx_transactions",
            json=prepare_transaction_post_request(
                payment_account_id=payment_account_id
            ),
        )
        assert response.status_code == 201
        mx_transaction: dict = response.json()
        assert mx_transaction["id"]
        assert mx_transaction["ledger_id"]
        mx_ledger_id = mx_transaction["ledger_id"]

        # post process ledger request
        process_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/process",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert process_ledger_response.status_code == 200
        mx_ledger: dict = process_ledger_response.json()
        assert mx_ledger["state"] == MxLedgerStateType.PROCESSING

        # post submit ledger request
        submit_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/submit",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert submit_ledger_response.status_code == 200
        submitted_mx_ledger: dict = submit_ledger_response.json()
        assert submitted_mx_ledger["state"] == MxLedgerStateType.SUBMITTED

        # submit the same ledger again and raise error
        submit_ledger_response = client.post(
            f"/ledger/api/v1/mx_ledgers/{mx_ledger_id}/submit",
            json={"mx_ledger_id": mx_ledger_id},
        )
        assert submit_ledger_response.status_code == 400
        error: dict = submit_ledger_response.json()
        assert error["error_code"] == LedgerErrorCode.MX_LEDGER_INVALID_PROCESS_STATE
        assert not error["retryable"]

    def test_create_mx_ledger_success(self, client: TestClient):
        payment_account_id = str(uuid.uuid4())
        create_mx_ledger_request = {
            "balance": 3000,
            "currency": Currency.USD.value,
            "payment_account_id": payment_account_id,
            "type": MxLedgerType.MICRO_DEPOSIT.value,
        }

        create_ledger_response = client.post(
            "/ledger/api/v1/mx_ledgers", json=create_mx_ledger_request
        )
        assert create_ledger_response.status_code == 201
        mx_ledger: dict = create_ledger_response.json()
        assert mx_ledger["id"]
