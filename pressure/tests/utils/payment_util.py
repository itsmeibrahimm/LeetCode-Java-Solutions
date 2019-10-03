import time

from payin_v1_client import PayerV1Api
from uuid import uuid4


class PaymentUtil:
    @staticmethod
    def get_payment_method_info(payer):
        return {
            "payer_id": payer.id,
            "payment_gateway": "stripe",
            "token": "tok_visa",
            "set_default": True,
            "is_scanned": True,
            "is_active": True,
        }

    @staticmethod
    def get_payer_info(
        dd_payer_id=int(time.time() * 1e6), country="US", payer_type="store"
    ):
        return {
            "dd_payer_id": "1",
            "payer_type": payer_type,
            "email": str(dd_payer_id) + "-" + payer_type + "@email.com",
            "country": country,
            "description": "payer creation for tests",
        }

    @staticmethod
    def create_payer(client):
        return PayerV1Api(client).create_payer_with_http_info(
            create_payer_request=PaymentUtil.get_payer_info(),
            _request_timeout=(5, 10),  # (connection, read) in seconds
        )

    @staticmethod
    def get_cart_payment_info(
        payer, payment_method, amount: int, country: str = "US", currency: str = "usd"
    ):
        return {
            "payer_id": payer.id,
            "payment_method_id": payment_method.id,
            "correlation_ids": {"reference_id": "1", "reference_type": "1"},
            "amount": amount,
            "payment_country": country,
            "currency": currency,
            "delay_capture": True,
            "idempotency_key": str(uuid4()),
            "client_description": "Transaction",
            "payer_statement_description": "Transaction",
            "metadata": {"reference_id": 1, "ct_reference_id": 1, "type": "OrderCart"},
        }
