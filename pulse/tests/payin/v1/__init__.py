import os

from payin_v1_client import ApiClient, Configuration

from ... import utils

from payin_v1_client import PayerV1Api, PaymentMethodV1Api, CartPaymentV1Api

STAGING_PULSE_API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", "")

payin_v1_configuration = Configuration(host=utils.SERVICE_URI)
payin_v1_configuration.verify_ssl = False
api_v1_client = ApiClient(configuration=payin_v1_configuration)
api_v1_client.set_default_header("x-api-key", STAGING_PULSE_API_KEY)
payer_v1_client = PayerV1Api(api_v1_client)
payment_method_v1_client = PaymentMethodV1Api(api_v1_client)
cart_payment_v1_client = CartPaymentV1Api(api_v1_client)
