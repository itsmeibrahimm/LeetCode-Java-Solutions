import stripe
import time

from . import payin_client_pulse

# TODO: Add stripe API key to bond service
API_KEY = "####"


class StripeUtil:
    @staticmethod
    def create_stripe_customer():
        stripe.api_key = API_KEY
        return stripe.Customer.create(
            description="Customer for jenny.rosen@example.com", source="tok_mastercard"
        )

    @staticmethod
    def get_stripe_customer_serial_id(stripe_customer_id):
        pass


class PaymentUtil:
    @staticmethod
    def get_payment_method_info(payer):
        return {
            "payer_id": payer["id"],
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }

    @staticmethod
    def get_payer_info(
        dd_payer_id=int(time.time() * 1e6), country="US", payer_type="marketplace"
    ):
        return {
            "dd_payer_id": dd_payer_id,
            "payer_type": payer_type,
            "email": str(dd_payer_id) + "-" + payer_type + "@email.com",
            "country": country,
            "description": "payer creation for tests",
        }

    @staticmethod
    def create_payer():
        return payin_client_pulse.create_payer_api_v1_payers_post_with_http_info(
            create_payer_request=PaymentUtil.get_payer_info()
        )

    @staticmethod
    def create_payment_method(payer_id: str, payer_id_type: str):
        if payer_id_type == "dd_payer_id":
            return payin_client_pulse.create_payment_method_api_v1_payment_methods_post(
                create_payment_method_request={
                    "payer_id": id,
                    "payment_gateway": "stripe",
                    "token": "tok_visa",
                }
            )
        elif payer_id_type == "stripe_customer_id":
            return payin_client_pulse.create_payment_method_api_v1_payment_methods_post(
                create_payment_method_request={
                    "payment_gateway": "stripe",
                    "token": "tok_visa",
                    "legacy_payment_info": {"stripe_customer_id": id},
                }
            )
