import stripe
from typing import Optional, Any
from app.commons.utils.pool import ThreadPoolHelper
from app.commons.providers import stripe_models as models
from app.commons.providers import errors


class StripeClientInterface:
    def create_connected_account_token(
        self,
        country: models.CountryCode,
        token: models.CreateConnectedAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.TokenId:
        """
        Create a token for another connected account (used for cross-country charges on stripe)
        See: https://stripe.com/docs/connect/shared-customers
        """
        ...

    def create_customer(
        self,
        country: models.CountryCode,
        request: models.CreateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.CustomerId:
        """
        Create a new Stripe Customer
        https://stripe.com/docs/api/customers
        """
        ...

    def update_customer(
        self,
        country: models.CountryCode,
        request: models.UpdateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> Any:
        """
        Update a Stripe Customer
        https://stripe.com/docs/api/customers/update
        """
        ...

    def create_payment_method(
        self,
        country: models.CountryCode,
        request: models.CreatePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Create a new Stripe Payment Method
        https://stripe.com/docs/api/payment_methods/create
        """
        ...

    def attach_payment_method(
        self,
        country: models.CountryCode,
        request: models.AttachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Attach a Stripe Payment Method to existing Stripe Customer
        https://stripe.com/docs/api/payment_methods/attach
        """
        ...

    def detach_payment_method(
        self,
        country: models.CountryCode,
        request: models.DetachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Attach a Stripe Payment Method to existing Stripe Customer
        https://stripe.com/docs/api/payment_methods/detach
        """
        ...

    def retrieve_payment_method(
        self,
        country: models.CountryCode,
        request: models.RetrievePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Retrieve a Stripe Payment Method
        https://stripe.com/docs/api/payment_methods/retrieve
        """
        ...

    def create_payment_intent(
        self,
        country: models.CountryCode,
        request: models.CreatePaymentIntent,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentIntentId:
        """
        Create a new PaymentIntent
        https://stripe.com/docs/api/payment_intents
        """
        ...

    def capture_payment_intent(
        self,
        country: models.CountryCode,
        request: models.CapturePaymentIntent,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentIntentStatus:
        """
        Capture a PaymentIntent
        https://stripe.com/docs/api/payment_intents
        """
        ...


class StripeClient(StripeClientInterface):
    """
    production stripe client
    """

    client_settings: models.SettingsByCountryCode

    def __init__(self, settings_list: models.SettingsList):
        if len(settings_list) == 0:
            raise ValueError("at least one client configuration needs to be provided")
        self.client_settings = {
            settings.country: settings for settings in settings_list
        }

    def settings_for(self, country: models.CountryCode) -> dict:
        try:
            return self.client_settings[country].client_settings
        except KeyError as err:
            raise errors.ServiceProviderException(
                f"service provider is not configured for country {country}"
            ) from err

    def create_connected_account_token(
        self,
        country: models.CountryCode,
        token: models.CreateConnectedAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.TokenId:
        try:
            stripe_token = stripe.Token.create(
                idempotency_key=idempotency_key,
                **self.settings_for(country),
                **token.dict(skip_defaults=True),
            )
            return stripe_token.id
        except stripe.error.InvalidRequestError as e:
            raise errors.InvalidRequestError() from e

    def create_customer(
        self,
        country: models.CountryCode,
        request: models.CreateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.CustomerId:
        customer = stripe.Customer.create(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return customer.id

    def update_customer(
        self,
        country: models.CountryCode,
        request: models.UpdateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> Any:
        customer = stripe.Customer.modify(
            # idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return customer

    def create_payment_method(
        self,
        country: models.CountryCode,
        request: models.CreatePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        payment_method = stripe.PaymentMethod.create(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_method

    def attach_payment_method(
        self,
        country: models.CountryCode,
        request: models.AttachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        payment_method = stripe.PaymentMethod.attach(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_method

    def detach_payment_method(
        self,
        country: models.CountryCode,
        request: models.DetachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        payment_method = stripe.PaymentMethod.detach(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_method

    def retrieve_payment_method(
        self,
        country: models.CountryCode,
        request: models.RetrievePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        payment_method = stripe.PaymentMethod.retrieve(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_method

    def create_payment_intent(
        self,
        country: models.CountryCode,
        request: models.CreatePaymentIntent,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentIntentId:
        payment_intent = stripe.PaymentIntent.create(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_intent.id

    def capture_payment_intent(
        self,
        country: models.CountryCode,
        request: models.CapturePaymentIntent,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentIntentStatus:
        payment_intent = stripe.PaymentIntent.capture(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_intent.status


class StripeTestClient(StripeClient):
    """
    stripe client for testing only
    includes methods that should not be called outside of tests
    (eg. credit card creation)
    """

    def create_bank_account_token(
        self,
        country: models.CountryCode,
        token: models.CreateBankAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ):
        return stripe.Token.create(
            idempotency_key=idempotency_key,
            bank_account=token.dict(),
            **self.settings_for(country),
        )

    def create_credit_card_token(
        self,
        country: models.CountryCode,
        token: models.CreateCreditCardToken,
        idempotency_key: models.IdempotencyKey = None,
    ):
        return stripe.Charge.create(
            idempotency_key=idempotency_key,
            country=country,
            card=token.dict(),
            **self.settings_for(country),
        )


class StripeClientPool(ThreadPoolHelper):
    # worker prefix
    prefix = "stripe"

    def __init__(
        self,
        settings_list: models.SettingsList = None,
        max_workers: Optional[int] = None,
        client: Optional[StripeClient] = None,
    ):
        # ensure threadpool workers get the right prefix
        if client is not None:
            self.client = client
        elif settings_list is not None:
            self.client = StripeClient(settings_list)
        else:
            raise ValueError(
                "either a Stripe Client `client` or the client `settings_list` must be specified"
            )

        super().__init__(max_workers=max_workers)

    async def create_connected_account_token(
        self,
        country: models.CountryCode,
        token: models.CreateConnectedAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.TokenId:
        return await self.submit(
            self.client.create_connected_account_token,
            country,
            token,
            idempotency_key=idempotency_key,
        )

    async def create_customer(
        self,
        country: models.CountryCode,
        request: models.CreateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.CustomerId:
        return await self.submit(
            self.client.create_customer,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def update_customer(
        self,
        country: models.CountryCode,
        request: models.UpdateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> Any:
        return await self.submit(
            self.client.update_customer,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def create_payment_method(
        self,
        country: models.CountryCode,
        request: models.CreatePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.create_payment_method,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def attach_payment_method(
        self,
        country: models.CountryCode,
        request: models.AttachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.attach_payment_method,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def detach_payment_method(
        self,
        country: models.CountryCode,
        request: models.DetachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.detach_payment_method,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def retrieve_payment_method(
        self,
        country: models.CountryCode,
        request: models.RetrievePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.retrieve_payment_method,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def create_payment_intent(
        self,
        country: models.CountryCode,
        request: models.CreatePaymentIntent,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentIntentId:
        return await self.submit(
            self.client.create_payment_intent,
            country,
            request,
            idempotency_key=idempotency_key,
        )

    async def capture_payment_intent(
        self,
        country: models.CountryCode,
        request: models.CapturePaymentIntent,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentIntentStatus:
        return await self.submit(
            self.client.capture_payment_intent,
            country,
            request,
            idempotency_key=idempotency_key,
        )
