from starlette.testclient import TestClient

TRANSACTION_ENDPOINT = "/payout/api/v1/transactions"


def list_transactions_url():
    return TRANSACTION_ENDPOINT + "/"


class TestTransactionV1:
    def test_list_transactions(self, client: TestClient):
        # TODO: add test cases here after PAYOUT-305: POST transaction endpoint is done
        pass

    def test_reverse_transactions(self, client: TestClient):
        # TODO: add test cases here after PAYOUT-305: POST transaction endpoint is done
        pass
