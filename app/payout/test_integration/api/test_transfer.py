import pytest
from starlette.testclient import TestClient
from datetime import datetime

from app.payout.types import StripePayoutStatus
from app.testcase_utils import validate_expected_items_in_dict

TRANSFER_ENDPOINT = "/payout/api/v0/transfers"
STRIPE_TRANSFER_ENDPOINT = "/payout/api/v0/transfers/stripe"


def create_transfer_url():
    return TRANSFER_ENDPOINT + "/"


def get_transfer_by_id_url(id: int):
    return f"{TRANSFER_ENDPOINT}/{id}"


def update_transfer_by_id_url(id: int):
    return f"{TRANSFER_ENDPOINT}/{id}"


def create_stripe_transfer_url():
    return STRIPE_TRANSFER_ENDPOINT + "/"


def get_stripe_transfer_by_id_url(id: int):
    return f"{STRIPE_TRANSFER_ENDPOINT}/{id}"


def update_stripe_transfer_by_id_url(id: int):
    return f"{STRIPE_TRANSFER_ENDPOINT}/{id}"


def get_stripe_transfer_by_stripe_id_url(stripe_id: str):
    return f"/payout/api/v0/transfers/stripe/_get-by-stripe-id?stripe_id={stripe_id}"


def get_stripe_transfer_by_transfer_id_url(transfer_id: int):
    return (
        f"/payout/api/v0/transfers/stripe/_get-by-transfer-id?transfer_id={transfer_id}"
    )


def delete_stripe_transfer_by_stripe_id_url(stripe_id: str):
    return f"/payout/api/v0/transfers/stripe/_delete-by-stripe-id?stripe_id={stripe_id}"


class TestTransferV0:
    @pytest.fixture
    def prepared_transfer(self, client: TestClient) -> dict:
        transfer_to_create = {
            "subtotal": 123,
            "adjustments": "some-adjustment",
            "amount": 123,
            "method": "stripe",
            "currency": "currency",
            "submitted_at": "2019-08-20T05:34:53+00:00",
            "deleted_at": "2019-08-20T05:34:53+00:00",
            "manual_transfer_reason": "manual_transfer_reason",
            "status": "status",
            "status_code": "status_code",
            "submitting_at": "2019-08-20T05:34:53+00:00",
            "should_retry_on_failure": True,
            "statement_description": "statement_description",
            "created_by_id": 123,
            "deleted_by_id": 321,
            "payment_account_id": 123,
            "recipient_id": 321,
            "recipient_ct_id": 123,
            "submitted_by_id": 321,
        }

        response = client.post(create_transfer_url(), json=transfer_to_create)
        assert response.status_code == 201
        created = response.json()

        validate_expected_items_in_dict(expected=transfer_to_create, actual=created)

        return created

    @pytest.fixture
    def prepared_stripe_transfer(self, prepared_transfer: dict, client: TestClient):
        to_create = {
            "stripe_status": StripePayoutStatus.New.value,
            "transfer_id": prepared_transfer["id"],
            "stripe_id": f"stripe_id-{datetime.utcnow()}",
            "stripe_request_id": "stripe_request_id",
            "stripe_failure_code": "stripe_failure_code",
            "stripe_account_id": "stripe_account_id",
            "stripe_account_type": "stripe_account_type",
            "country_shortname": "country_shortname",
            "bank_last_four": "bank_last_four",
            "bank_name": "bank_name",
            "submission_error_code": "submission_error_code",
            "submission_error_type": "submission_error_type",
            "submission_status": "submission_status",
            "submitted_at": "2019-08-20T05:34:53+00:00",
        }

        response = client.post(create_stripe_transfer_url(), json=to_create)
        assert response.status_code == 201
        created: dict = response.json()
        validate_expected_items_in_dict(expected=to_create, actual=created)
        return created

    def test_invalid(self, client: TestClient):
        response = client.get(TRANSFER_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

        response = client.get(STRIPE_TRANSFER_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_get_update_transfer(
        self, prepared_transfer: dict, client: TestClient
    ):
        adjustment_update = "updated_adjustment"
        response = client.patch(
            update_transfer_by_id_url(prepared_transfer["id"]),
            json={"adjustments": adjustment_update},
        )

        assert response.status_code == 200
        transfer_updated: dict = response.json()
        assert transfer_updated["adjustments"] == adjustment_update

        response = client.get(get_transfer_by_id_url(prepared_transfer["id"]))

        assert response.status_code == 200
        transfer_got: dict = response.json()
        assert transfer_got.items() == transfer_updated.items()

    def test_get_transfer_by_id_not_found(self, client: TestClient):
        response = client.get(get_transfer_by_id_url(-1))
        assert response.status_code == 404

    def test_update_transfer_by_id_not_found(self, client: TestClient):
        response = client.patch(update_transfer_by_id_url(-1), json={"subtotal": 100})
        assert response.status_code == 404

    def test_create_get_update_stripe_transfer(
        self, prepared_stripe_transfer: dict, client: TestClient
    ):
        stripe_status_update = StripePayoutStatus.New.value
        response = client.patch(
            update_stripe_transfer_by_id_url(prepared_stripe_transfer["id"]),
            json={"stripe_status": stripe_status_update},
        )

        assert response.status_code == 200
        updated: dict = response.json()

        assert updated["stripe_status"] == stripe_status_update

        response = client.get(
            get_stripe_transfer_by_id_url(prepared_stripe_transfer["id"])
        )

        assert response.status_code == 200
        got: dict = response.json()
        assert updated.items() == got.items()

    def test_get_stripe_transfer_by_stripe_id(
        self, prepared_stripe_transfer: dict, client: TestClient
    ):
        response = client.get(
            get_stripe_transfer_by_stripe_id_url(prepared_stripe_transfer["stripe_id"])
        )
        assert response.status_code == 200
        assert prepared_stripe_transfer.items() == response.json().items()

    def test_get_stripe_transfer_by_transfer_id(
        self, prepared_stripe_transfer: dict, client: TestClient
    ):
        response = client.get(
            get_stripe_transfer_by_transfer_id_url(
                prepared_stripe_transfer["transfer_id"]
            )
        )
        assert response.status_code == 200
        assert prepared_stripe_transfer.items() == response.json()[0].items()

    def test_delete_stripe_transfer_by_stripe_id(
        self, prepared_stripe_transfer: dict, client: TestClient
    ):
        response = client.delete(
            delete_stripe_transfer_by_stripe_id_url(
                prepared_stripe_transfer["stripe_id"]
            )
        )
        assert response.status_code == 200
        assert {
            "acknowledged": True,
            "affected_record_count": 1,
        }.items() == response.json().items()

    def test_get_stripe_transfer_by_id_not_found(self, client: TestClient):
        response = client.get(get_stripe_transfer_by_id_url(-1))
        assert response.status_code == 404

    def test_update_stripe_transfer_by_id_not_found(self, client: TestClient):
        response = client.patch(
            update_stripe_transfer_by_id_url(-1),
            json={"stripe_status": StripePayoutStatus.New.value},
        )
        assert response.status_code == 404

    def test_get_stripe_transfer_by_stripe_id_not_found(self, client: TestClient):
        response = client.get(get_stripe_transfer_by_stripe_id_url("nothing"))
        assert response.status_code == 200

    def test_get_stripe_transfer_by_transfer_id_not_found(self, client: TestClient):
        response = client.get(get_stripe_transfer_by_transfer_id_url(99999))
        assert response.status_code == 200
