from pytest import fixture
from starlette.testclient import TestClient
from datetime import datetime

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
    @fixture
    def prepared_transfer(self, client: TestClient) -> dict:
        transfer_to_create = {
            "subtotal": 123,
            "adjustments": "some-adjustment",
            "amount": 123,
            "method": "stripe",
        }

        response = client.post(create_transfer_url(), json=transfer_to_create)
        assert response.status_code == 201
        created = response.json()
        assert transfer_to_create.items() <= created.items()
        return created

    @fixture
    def prepared_stripe_transfer(self, prepared_transfer: dict, client: TestClient):
        to_create = {
            "stripe_status": "default",
            "stripe_id": f"stripe_id-{datetime.utcnow()}",
            "transfer_id": prepared_transfer["id"],
        }
        response = client.post(create_stripe_transfer_url(), json=to_create)
        assert response.status_code == 201
        created: dict = response.json()
        assert to_create.items() <= created.items()
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
        stripe_status_update = "newstatus"
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
        assert {"acknowledged": True}.items() == response.json().items()

    def test_get_stripe_transfer_by_id_not_found(self, client: TestClient):
        response = client.get(get_stripe_transfer_by_id_url(-1))
        assert response.status_code == 404

    def test_update_stripe_transfer_by_id_not_found(self, client: TestClient):
        response = client.patch(
            update_stripe_transfer_by_id_url(-1), json={"stripe_status": "new"}
        )
        assert response.status_code == 404

    def test_get_stripe_transfer_by_stripe_id_not_found(self, client: TestClient):
        response = client.get(get_stripe_transfer_by_stripe_id_url("nothing"))
        assert response.status_code == 200

    def test_get_stripe_transfer_by_transfer_id_not_found(self, client: TestClient):
        response = client.get(get_stripe_transfer_by_transfer_id_url(99999))
        assert response.status_code == 200
