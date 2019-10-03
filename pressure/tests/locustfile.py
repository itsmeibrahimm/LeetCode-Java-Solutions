from locust import task
from payout_v0_client import AccountsV0Api, DefaultApi, PaymentAccountCreate
from payin_v1_client import PaymentMethodV1Api, CartPaymentV1Api
from utils.payment_locust import PayoutV0Locust, PayinV1Locust
from utils.payment_util import PaymentUtil


class PayinV1Tests(PayinV1Locust):
    class Task(PayinV1Locust.PayinV1TaskSet):

        CART_AMOUNT = 1000

        @task(1)
        def test_create_cart_payment(self):
            new_payer = PaymentUtil.create_payer(self.client)[0]
            new_payment_method = PaymentMethodV1Api(self.client).create_payment_method(
                create_payment_method_request_v1=PaymentUtil.get_payment_method_info(
                    new_payer
                ),
                _request_timeout=(5, 20),  # (connection, read) in seconds
            )
            new_cart_payment = CartPaymentV1Api(
                self.client
            ).create_cart_payment_with_http_info(
                create_cart_payment_request=PaymentUtil.get_cart_payment_info(
                    new_payer, new_payment_method, self.CART_AMOUNT
                ),
                _request_timeout=(5, 15),  # (connection, read) in seconds
            )
            assert new_cart_payment[1] == 201
            assert new_cart_payment[0].amount == self.CART_AMOUNT

    weight = 1
    task_set = Task
    min_wait = 5000
    max_wait = 15000


class PayoutV0Tests(PayoutV0Locust):
    class Task(PayoutV0Locust.PayoutV0TaskSet):
        @task(50)
        def test_create_account(self):
            AccountsV0Api(self.client).create_payment_account(
                PaymentAccountCreate(statement_descriptor=f"pressure-test")
            )

        @task(50)
        def test_webhook(self):
            data = {
                "id": "evt_1DAJwRHe1ypiIBRU4Gs6xdtz",
                "object": "event",
                "account": "acct_1CE3vpHe1ypiIBRU",
                "api_version": "2016-02-29",
                "created": 1567648158,
                "livemode": True,
                "pending_webhooks": 2,
                "request": None,
                "type": "transfer.paid",
                "user_id": "acct_1CE3vpHe1ypiIBRU",
                "data": {
                    "object": {
                        "id": "po_1DAJwJHe1ypiIBRUhxGi4yLw",
                        "object": "transfer",
                        "amount": 101,
                        "arrival_date": 1536941682,
                        "automatic": False,
                        "balance_transaction": "txn_1DAJwJHe1ypiIBRUquKKX1Ky",
                        "created": 1536941679,
                        "currency": "usd",
                        "description": None,
                        "destination": "card_1DA1yTHe1ypiIBRU3mGv3mWK",
                        "failure_balance_transaction": None,
                        "failure_code": None,
                        "failure_message": None,
                        "livemode": True,
                        "metadata": {"service_origin": "bank-service"},
                        "method": "instant",
                        "source_type": "card",
                        "statement_descriptor": "Doordash, Inc. FastPay",
                        "status": "paid",
                        "type": "card",
                        "amount_reversed": 0,
                        "application_fee": None,
                        "card": {
                            "id": "card_1DA1yTHe1ypiIBRU3mGv3mWK",
                            "object": "card",
                            "account": "acct_1CE3vpHe1ypiIBRU",
                            "address_city": None,
                            "address_country": None,
                            "address_line1": None,
                            "address_line1_check": None,
                            "address_line2": None,
                            "address_state": None,
                            "address_zip": None,
                            "address_zip_check": None,
                            "available_payout_methods": ["standard", "instant"],
                            "brand": "Visa",
                            "country": "US",
                            "currency": "usd",
                            "cvc_check": "pass",
                            "default_for_currency": False,
                            "dynamic_last4": None,
                            "exp_month": 8,
                            "exp_year": 2021,
                            "fingerprint": "FzfRBTlBCWpcBf4V",
                            "funding": "debit",
                            "last4": "9417",
                            "metadata": {},
                            "name": None,
                            "tokenization_method": None,
                        },
                        "date": 1536941682,
                        "recipient": None,
                        "reversals": {
                            "object": "list",
                            "data": [],
                            "has_more": None,
                            "total_count": 0,
                            "url": "/v1/transfers/po_1DAJwJHe1ypiIBRUhxGi4yLw/reversals",
                        },
                        "reversed": False,
                        "source_transaction": None,
                        "transfer_group": None,
                    },
                    "previous_attributes": {
                        "arrival_date": 1536941679,
                        "status": "pending",
                        "date": 1536941679,
                    },
                },
            }
            DefaultApi(self.client).handle_webhook_event_webhook_country_code_post(
                "US", body=data
            )

    weight = 1
    task_set = Task
    min_wait = 5000
    max_wait = 15000
