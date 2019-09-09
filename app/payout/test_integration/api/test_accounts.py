from starlette.testclient import TestClient

from app.testcase_utils import validate_expected_items_in_dict

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
            "account_id": 123,
            "account_type": "sma",
            "entity": "dasher",
            "resolve_outstanding_balance_frequency": "daily",
            "payout_disabled": True,
            "charges_enabled": True,
            "old_account_id": 1234,
            "upgraded_to_managed_account_at": "2019-08-20T05:34:53+00:00",
            "is_verified_with_stripe": True,
            "transfers_enabled": True,
            "statement_descriptor": "test_statement_descriptor",
        }

        #  Create
        response = client.post(create_account_url(), json=account_to_create)
        assert response.status_code == 201
        account_created: dict = response.json()

        validate_expected_items_in_dict(
            expected=account_to_create, actual=account_created
        )

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
        account_to_create = {
            "stripe_id": "stripe_id",
            "country_shortname": "us",
            "stripe_last_updated_at": "2019-08-20T05:34:53+00:00",
            "bank_account_last_updated_at": "2019-08-20T05:34:53+00:00",
            "fingerprint": "fingerprint",
            "default_bank_last_four": "last4",
            "default_bank_name": "bank",
            "verification_disabled_reason": "no-reason",
            "verification_due_by": "2019-08-20T05:34:53+00:00",
            "verification_fields_needed": ["a lot"],
        }

        # Create
        response = client.post(
            create_stripe_managed_account_url(), json=account_to_create
        )
        assert response.status_code == 201

        account_created: dict = response.json()

        validate_expected_items_in_dict(
            expected=account_to_create, actual=account_created
        )

        # Update
        verification_fields_needed = ["need!"]
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
            json={"verification_fields_needed": ["everything!"]},
        )

        assert response.status_code == 404
