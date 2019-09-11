from starlette.testclient import TestClient

ACCOUNT_ENDPOINT = "/payout/api/v1/accounts"


def create_account_url():
    return ACCOUNT_ENDPOINT + "/"


def get_account_by_id_url(id: int):
    return f"{ACCOUNT_ENDPOINT}/{id}"


class TestAccountV1:
    def test_invalid(self, client: TestClient):
        response = client.get(ACCOUNT_ENDPOINT + "/")
        assert response.status_code == 405, "accessing accounts requires an id"

    def test_create_get_payment_account(self, client: TestClient):
        account_to_create = {
            "target_id": 1,
            "target_type": "dasher",
            "country": "US",
            "currency": "usd",
            "statement_descriptor": "test_statement_descriptor",
        }

        #  Create
        response = client.post(create_account_url(), json=account_to_create)
        assert response.status_code == 201
        account_created: dict = response.json()
        assert (
            account_created["statement_descriptor"]
            == account_to_create["statement_descriptor"]
        )

        #  Get
        response = client.get(get_account_by_id_url(account_created["id"]))

        assert response.status_code == 200
        account_got_by_id: dict = response.json()
        assert account_got_by_id == account_created
