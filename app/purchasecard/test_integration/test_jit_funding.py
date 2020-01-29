from starlette.status import HTTP_200_OK
from starlette.testclient import TestClient


class TestMarqetaJITFunding:
    def test_jit_funding_route(self, client: TestClient):
        request_body = {
            "acting_user_token": "123",
            "gpa_order": {
                "funding_source_token": "**********d07e",
                "funding": {
                    "source": {
                        "is_default_account": False,
                        "name": "DoorDash Program Gateway Funding Source",
                        "last_modified_time": "2016-01-22T21:16:05Z",
                        "created_time": "2016-01-22T21:16:05Z",
                        "token": "**********d07e",
                        "active": True,
                        "type": "programgateway",
                    },
                    "amount": 9.58,
                },
                "transaction_token": "123",
                "amount": 9.58,
                "state": "PENDING",
                "user_token": "123",
                "token": "123",
                "jit_funding": {
                    "acting_user_token": "123",
                    "amount": 9.58,
                    "user_token": "123",
                    "token": "123",
                    "address_verification": {
                        "request": {"zip": "43201    ", "street_address": "     "},
                        "issuer": {
                            "on_file": {
                                "zip": "60061",
                                "street_address": "595 N Lakeview Parkway",
                            },
                            "response": {
                                "memo": "Address not present and zip code not match",
                                "code": "0201",
                            },
                        },
                    },
                    "method": "pgfs.authorization",
                },
                "currency_code": "USD",
            },
            "issuer_payment_node": "123",
            "user_token": "1928383",
            "created_time": "2020-01-28T01:16:26Z",
            "card_token": "card-3804025",
            "request_amount": 9.58,
            "acquirer": {
                "institution_id_code": "123",
                "system_trace_audit_number": "123",
                "retrieval_reference_number": "123",
            },
            "currency_conversion": {
                "network": {
                    "conversion_rate": 1,
                    "original_amount": 9.58,
                    "original_currency_code": "840",
                }
            },
            "network": "MASTERCARD",
            "gpa": {
                "ledger_balance": 38.81,
                "credit_balance": 0,
                "balances": {
                    "USD": {
                        "credit_balance": 0,
                        "available_balance": 0,
                        "ledger_balance": 38.81,
                        "pending_credits": 0,
                        "currency_code": "USD",
                    }
                },
                "available_balance": 0,
                "pending_credits": 0,
                "currency_code": "USD",
            },
            "state": "PENDING",
            "issuer_received_time": "2020-01-28T01:16:26.396Z",
            "type": "authorization",
            "settlement_date": "2020-01-27T00:00:00Z",
            "user": {"metadata": {}},
            "card_acceptor": {
                "city": "CHICAGO",
                "name": "WENDYS #1206",
                "zip": "60622",
                "country": "USA",
                "mcc": "5814",
                "mid": "123",
                "mcc_groups": ["group"],
                "state": "IL",
                "poi": {
                    "pin_present": "false",
                    "card_presence": "0",
                    "partial_approval_capable": "0",
                    "cardholder_presence": "0",
                    "tid": "35717012",
                    "processing_type": "MANUAL",
                    "channel": "OTHER",
                },
                "network_mid": "4445155035717",
            },
            "card": {"last_four": "6288", "metadata": {}},
            "acquirer_fee_amount": 0,
            "user_transaction_time": "2020-01-28T01:16:26Z",
            "amount": 9.58,
            "token": "token",
            "currency_code": "USD",
        }
        response = client.post(
            "/purchasecard/api/v0/marqeta/jit_funding", json=request_body
        )

        assert response.status_code == HTTP_200_OK
