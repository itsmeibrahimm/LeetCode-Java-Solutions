from payin_v0_client import (
    ApiClient,
    Configuration,
    PayerV0Api,
    PaymentMethodV0Api,
    CartPaymentV0Api,
    DisputeV0Api,
)

from ...utils import SERVICE_URI

import os

STAGING_PULSE_API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", "")

payin_v0_configuration = Configuration(host=SERVICE_URI)
payin_v0_configuration.verify_ssl = False
api_v0_client = ApiClient(configuration=payin_v0_configuration)
api_v0_client.set_default_header("x-api-key", STAGING_PULSE_API_KEY)
payer_v0_client = PayerV0Api(api_v0_client)
dispute_v0_client = DisputeV0Api(api_v0_client)
payment_method_v0_client = PaymentMethodV0Api(api_v0_client)
cart_payment_v0_client = CartPaymentV0Api(api_v0_client)
