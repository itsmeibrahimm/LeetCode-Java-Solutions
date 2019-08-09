from starlette.testclient import TestClient

ACCOUNT_ENDPOINT = "/payout/api/v0/accounts"
SMA_ENDPOINT = "/payout/api/v0/accounts/stripe"


def create_account_url():
    return ACCOUNT_ENDPOINT + "/"


def get_account_by_id_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}"


def update_account_by_id_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}"


def get_account_by_account_type_account_id_url(account_type: str, account_id: int):
    return f"{ACCOUNT_ENDPOINT}/_get-by-stripe-account-type-account-id?stripe_account_id={account_id}&stripe_account_type={account_type}"


def create_stripe_managed_account_url():
    return SMA_ENDPOINT + "/"


def get_stripe_managed_account_by_id_url(id: int):
    return f"{SMA_ENDPOINT}/{id}"


def update_stripe_managed_account_by_id_url(id: int):
    return f"{SMA_ENDPOINT}/{id}"


class TestAccountV0:
    def test_invalid(self, client: TestClient):
        response = client.get(ACCOUNT_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

        response = client.get(SMA_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_get_update_payment_account(self, client: TestClient):
        account_to_create = {
            "statement_descriptor": "yup",
            "account_type": "blah",
            "account_id": 123,
            "entity": "entity",
        }

        #  Create
        response = client.post(create_account_url(), json=account_to_create)
        assert response.status_code == 201
        account_created: dict = response.json()
        assert account_to_create.items() <= account_created.items()

        # Update
        statement_descriptor_updated = "new yup"
        response = client.patch(
            update_account_by_id_url(account_created["id"]),
            json={"statement_descriptor": statement_descriptor_updated},
        )

        assert response.status_code == 200
        account_updated = response.json()
        assert account_updated["statement_descriptor"] == statement_descriptor_updated

        #  Get
        response = client.get(get_account_by_id_url(account_created["id"]))

        assert response.status_code == 200
        account_got_by_id: dict = response.json()
        assert account_got_by_id.items() == account_updated.items()

        #  Get by type and account_id
        response = client.get(
            get_account_by_account_type_account_id_url(
                account_got_by_id["account_type"], account_got_by_id["account_id"]
            )
        )
        assert response.status_code == 200
        accounts_got_by_account_id_type: dict = response.json()
        assert (
            accounts_got_by_account_id_type[0]["account_id"]
            == account_got_by_id["account_id"]  # noqa: W503
        )
        assert (
            accounts_got_by_account_id_type[0]["account_type"]
            == account_got_by_id["account_type"]  # noqa: W503
        )

    def test_get_payment_account_by_id_not_found(self, client: TestClient):
        response = client.get(get_account_by_id_url(9999))
        assert response.status_code == 404

    def test_get_payment_account_by_account_type_account_id_not_found(
        self, client: TestClient
    ):
        response = client.get(
            get_account_by_account_type_account_id_url("nothing", 9999)
        )
        assert "id" not in response.json()

    def test_update_payment_account_by_id_not_found(self, client: TestClient):
        response = client.patch(
            update_account_by_id_url(9999), json={"statement_descriptor": "something"}
        )

        assert response.status_code == 404

    def test_create_get_update_stripe_managed_account(self, client: TestClient):
        account_to_create = {"stripe_id": "stripe123", "country_shortname": "us"}

        # Create
        response = client.post(
            create_stripe_managed_account_url(), json=account_to_create
        )
        assert response.status_code == 201

        account_created: dict = response.json()

        assert account_to_create.items() <= account_created.items()

        # Update
        verification_fields_needed = "need!"
        response = client.patch(
            update_stripe_managed_account_by_id_url(account_created["id"]),
            json={"verification_fields_needed": verification_fields_needed},
        )

        account_updated = response.json()
        assert (
            account_updated["verification_fields_needed"] == verification_fields_needed
        )
        # Get
        response = client.get(
            get_stripe_managed_account_by_id_url(account_updated["id"])
        )
        account_got: dict = response.json()
        assert account_got.items() == account_updated.items()

    def test_get_stripe_managed_account_not_found(self, client: TestClient):
        response = client.get(get_stripe_managed_account_by_id_url(9999))
        assert response.status_code == 404

    def test_update_stripe_managed_account_by_id_not_found(self, client: TestClient):
        response = client.patch(
            update_stripe_managed_account_by_id_url(9999),
            json={"verification_fields_needed": "everything!"},
        )

        assert response.status_code == 404
