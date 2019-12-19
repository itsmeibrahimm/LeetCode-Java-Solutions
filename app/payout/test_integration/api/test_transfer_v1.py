from starlette.testclient import TestClient
from app.payout.core.exceptions import PayoutErrorCode
from app.payout.models import TransferMethodType, TransferType
from app.payout.repository.maindb.model.transfer import TransferStatus
from datetime import datetime, timezone
from app.payout.test_integration.api import (
    get_transfer_by_id_url,
    submit_transfer_url,
    list_transfers_url,
    create_transfer_url,
    update_transfer_url,
)


class TestTransferV1:
    def test_create_transfer_failed_no_matching_payout_countries(
        self, client: TestClient, payout_account: dict, verified_payout_account: dict
    ):
        create_transfer_req = {
            "payout_account_id": payout_account["id"],
            "transfer_type": TransferType.SCHEDULED,
            "end_time": datetime.now(timezone.utc).isoformat(),
            "payout_countries": ["invalid_country"],
        }
        response = client.post(create_transfer_url(), json=create_transfer_req)
        assert response.status_code == 400
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.PAYOUT_COUNTRY_NOT_MATCH
        assert not error["retryable"]

    def test_create_transfer_failed_no_unpaid_transactions(
        self, client: TestClient, payout_account: dict
    ):
        create_transfer_req = {
            "payout_account_id": payout_account["id"],
            "transfer_type": TransferType.MANUAL,
            "end_time": datetime.now(timezone.utc).isoformat(),
        }
        response = client.post(create_transfer_url(), json=create_transfer_req)
        assert response.status_code == 400
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.NO_UNPAID_TRANSACTION_FOUND
        assert not error["retryable"]

    def test_create_then_get_transfer_by_id(
        self,
        client: TestClient,
        verified_payout_account: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        response = client.get(get_transfer_by_id_url(transfer["id"]))
        assert response.status_code == 200
        retrieved_transfer: dict = response.json()
        assert retrieved_transfer == transfer

    def test_get_transfer_by_id_not_found(self, client: TestClient):
        response = client.get(get_transfer_by_id_url(-1))
        assert response.status_code == 404
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.TRANSFER_NOT_FOUND
        assert not error["retryable"]

    def test_create_then_submit_transfer(
        self,
        client: TestClient,
        verified_payout_account_with_payout_card: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        submitted_by = 6666
        submit_transfer_req = {
            "method": TransferMethodType.STRIPE,
            "submitted_by": submitted_by,
        }
        response = client.post(
            submit_transfer_url(transfer["id"]), json=submit_transfer_req
        )
        assert response.status_code == 200

        retrieve_response = client.get(get_transfer_by_id_url(transfer["id"]))
        assert retrieve_response.status_code == 200
        retrieved_transfer: dict = retrieve_response.json()
        assert retrieved_transfer["submitted_by_id"] == submitted_by
        assert retrieved_transfer["status"] == TransferStatus.PENDING

    def test_create_then_submit_transfer_processing_error(
        self,
        client: TestClient,
        verified_payout_account_with_payout_card: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        submit_transfer_req = {"method": TransferMethodType.STRIPE, "retry": True}
        response = client.post(
            submit_transfer_url(transfer["id"]), json=submit_transfer_req
        )
        assert response.status_code == 200

        retrieve_response = client.get(get_transfer_by_id_url(transfer["id"]))
        assert retrieve_response.status_code == 200
        retrieved_transfer: dict = retrieve_response.json()
        assert retrieved_transfer["status"] == TransferStatus.PENDING

        response = client.post(
            submit_transfer_url(transfer["id"]), json=submit_transfer_req
        )
        assert response.status_code == 400
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.TRANSFER_PROCESSING
        assert not error["retryable"]

    def test_create_then_submit_transfer_duplicate_error(
        self,
        client: TestClient,
        verified_payout_account_with_payout_card: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        submit_transfer_req = {"method": TransferMethodType.STRIPE}
        response = client.post(
            submit_transfer_url(transfer["id"]), json=submit_transfer_req
        )
        assert response.status_code == 200

        retrieve_response = client.get(get_transfer_by_id_url(transfer["id"]))
        assert retrieve_response.status_code == 200
        retrieved_transfer: dict = retrieve_response.json()
        assert retrieved_transfer["status"] == TransferStatus.PENDING

        response = client.post(
            submit_transfer_url(transfer["id"]), json=submit_transfer_req
        )
        assert response.status_code == 400
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.DUPLICATE_TRANSFER
        assert not error["retryable"]

    def test_create_then_list_transfers_invalid_input(
        self,
        client: TestClient,
        verified_payout_account: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        list_transfers_req = {"is_submitted": True}
        response = client.get(list_transfers_url(), json=list_transfers_req)
        assert response.status_code == 400
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.UNSUPPORTED_USECASE
        assert not error["retryable"]

    def test_create_then_list_transfers_by_payment_account_ids(
        self,
        client: TestClient,
        verified_payout_account: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        list_transfers_req = {
            "payout_account_ids": [str(transfer["payment_account_id"])]
        }
        response = client.get(list_transfers_url(), params=list_transfers_req)
        assert response.status_code == 200
        response_dict: dict = response.json()
        assert response_dict["count"] == 1
        assert response_dict["transfer_list"][0] == transfer

    def test_create_then_list_transfers_by_status_and_amount(
        self,
        client: TestClient,
        verified_payout_account: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        list_transfers_req = {"status": TransferStatus.NEW}
        response = client.get(list_transfers_url(), params=list_transfers_req)
        assert response.status_code == 200
        response_dict: dict = response.json()
        assert response_dict["count"] >= 1
        assert transfer in response_dict["transfer_list"]

    def test_create_then_list_transfers_with_stripe_transfer(
        self,
        client: TestClient,
        verified_payout_account_with_payout_card: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        list_transfers_req = {"has_positive_amount": True, "is_submitted": True}
        submit_transfer_req = {"method": TransferMethodType.STRIPE}
        client.post(submit_transfer_url(transfer["id"]), json=submit_transfer_req)
        response = client.get(get_transfer_by_id_url(transfer["id"]))
        retrieved_transfer: dict = response.json()

        response = client.get(list_transfers_url(), params=list_transfers_req)
        assert response.status_code == 200
        response_dict: dict = response.json()
        assert response_dict["count"] >= 1
        assert retrieved_transfer in response_dict["transfer_list"]

    def test_create_then_list_positive_amount_transfers(
        self,
        client: TestClient,
        verified_payout_account: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        list_transfers_req = {"has_positive_amount": True}
        response = client.get(list_transfers_url(), params=list_transfers_req)
        assert response.status_code == 200
        response_dict: dict = response.json()
        assert response_dict["count"] >= 1
        assert transfer in response_dict["transfer_list"]

    def test_create_then_update_transfer(
        self,
        client: TestClient,
        verified_payout_account: dict,
        new_transaction: dict,
        transfer: dict,
    ):
        assert transfer["status"] == "new"
        update_transfer_req = {"status": "pending"}
        response = client.post(
            update_transfer_url(transfer_id=transfer["id"]), json=update_transfer_req
        )
        assert response.status_code == 200
        updated_transfer: dict = response.json()
        assert updated_transfer["id"] == transfer["id"]
        assert updated_transfer["status"] == "pending"

    def test_update_transfer_not_found(self, client: TestClient):
        update_transfer_req = {"status": "pending"}
        response = client.post(
            update_transfer_url(transfer_id=-1), json=update_transfer_req
        )
        assert response.status_code == 400
        error: dict = response.json()
        assert error["error_code"] == PayoutErrorCode.TRANSFER_NOT_FOUND
        assert not error["retryable"]
