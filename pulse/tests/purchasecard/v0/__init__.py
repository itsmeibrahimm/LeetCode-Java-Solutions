import os

from purchasecard_v0_client import ApiClient, Configuration, UsersV0Api

SERVICE_URI = os.getenv("SERVICE_URI", "http://localhost:8082")
STAGING_PULSE_API_KEY = os.getenv("API_KEY_PAYMENT_SERVICE", "")

purchasecard_v0_configuration = Configuration(host=SERVICE_URI)
api_client = ApiClient(configuration=purchasecard_v0_configuration)
api_client.set_default_header("x-api-key", STAGING_PULSE_API_KEY)

user_client = UsersV0Api(api_client)
