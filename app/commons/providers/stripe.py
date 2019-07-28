import stripe
from typing import Optional
from app.commons.utils.pool import ThreadPoolHelper
from app.commons.providers import stripe_models as models
from app.commons.providers import errors


class StripeClientInterface:
    def create_connected_account_token(
        self, token: models.CreateConnectedAccountToken
    ) -> str:
        """
        Create a token for another connected account (used for cross-country charges on stripe)
        See: https://stripe.com/docs/connect/shared-customers
        """
        ...

    def create_customer(self, request: models.CreateCustomer) -> str:
        """
        Create a new Stripe Customer
        https://stripe.com/docs/api/customers
        """


class StripeClient(StripeClientInterface):
    """
    production stripe client
    """

    def __init__(self, api_key: str, country: str):
        self.api_key = api_key
        self.country = country

    def create_connected_account_token(
        self, token: models.CreateConnectedAccountToken
    ) -> str:
        try:
            stripe_token = stripe.Token.create(api_key=self.api_key, **token.dict())
            return stripe_token.id
        except stripe.error.InvalidRequestError as e:
            raise errors.InvalidRequestError() from e

    def create_customer(self, request: models.CreateCustomer) -> str:
        customer = stripe.Customer.create(api_key=self.api_key, **request.dict())
        return customer.id


class StripeTestClient(StripeClient):
    """
    stripe client for testing only
    includes methods that should not be called outside of tests
    (eg. credit card creation)
    """

    def create_bank_account_token(
        self, country: str, token: models.CreateBankAccountToken
    ):
        return stripe.Charge.create(
            api_key=self.api_key, country=country, bank_account=token.dict()
        )

    def create_credit_card_token(
        self, country: str, token: models.CreateCreditCardToken
    ):
        return stripe.Charge.create(
            api_key=self.api_key, country=country, card=token.dict()
        )


class StripePoolHelper(ThreadPoolHelper):
    api_key: str

    def __init__(
        self,
        api_key: str,
        country: str,
        max_workers: Optional[int] = None,
        client: Optional[StripeClient] = None,
    ):
        # ensure threadpool workers get the right prefix
        self.prefix = f"stripe-{country}"
        super().__init__(max_workers=max_workers)

        if client is not None:
            self.client = client
        elif api_key and country:
            self.client = StripeClient(api_key, country)
        else:
            raise ValueError(
                "a Stripe Client `client` or the `api_key` and `country` must be specified"
            )

    async def create_connected_account_token(
        self, token: models.CreateConnectedAccountToken
    ) -> str:
        return await self.submit(self.client.create_connected_account_token, token)

    async def create_customer(self, request: models.CreateCustomer) -> str:
        return await self.submit(self.client.create_customer, request)
