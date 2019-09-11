import stripe
import abc
from stripe.http_client import HTTPClient
from typing import Optional, Any

from app.commons import tracing
from app.commons.providers.stripe.stripe_http_client import (
    TimedRequestsClient,
    set_default_http_client,
)
from app.commons.providers import errors
from app.commons.providers.stripe import stripe_models as models
from app.commons.utils.pool import ThreadPoolHelper


class StripeClientInterface(metaclass=abc.ABCMeta):
    # TODO: Require idempotency key
    @abc.abstractmethod
    def create_connected_account_token(
        self,
        *,
        country: models.CountryCode,
        token: models.CreateConnectedAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.TokenId:
        """
        Create a token for another connected account (used for cross-country charges on stripe)
        See: https://stripe.com/docs/connect/shared-customers
        """
        ...

    @abc.abstractmethod
    def create_customer(
        self,
        *,
        country: models.CountryCode,
        request: models.CreateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.CustomerId:
        """
        Create a new Stripe Customer
        https://stripe.com/docs/api/customers
        """
        ...

    @abc.abstractmethod
    def update_customer(
        self,
        *,
        country: models.CountryCode,
        request: models.UpdateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> Any:
        """
        Update a Stripe Customer
        https://stripe.com/docs/api/customers/update
        """
        ...

    @abc.abstractmethod
    def create_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.CreatePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Create a new Stripe Payment Method
        https://stripe.com/docs/api/payment_methods/create
        """
        ...

    @abc.abstractmethod
    def attach_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.AttachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Attach a Stripe Payment Method to existing Stripe Customer
        https://stripe.com/docs/api/payment_methods/attach
        """
        ...

    @abc.abstractmethod
    def detach_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.DetachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Attach a Stripe Payment Method to existing Stripe Customer
        https://stripe.com/docs/api/payment_methods/detach
        """
        ...

    @abc.abstractmethod
    def retrieve_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.RetrievePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        """
        Retrieve a Stripe Payment Method
        https://stripe.com/docs/api/payment_methods/retrieve
        """
        ...

    @abc.abstractmethod
    def create_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CreatePaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntent:
        """
        Create a new PaymentIntent
        https://stripe.com/docs/api/payment_intents
        """
        ...

    @abc.abstractmethod
    def capture_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CapturePaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntent:
        """
        Capture a PaymentIntent
        https://stripe.com/docs/api/payment_intents
        """
        ...

    @abc.abstractmethod
    def cancel_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CancelPaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntentId:
        """
        Cancel a PaymentIntent
        https://stripe.com/docs/api/payment_intents
        """
        ...

    @abc.abstractmethod
    def refund_charge(
        self,
        *,
        country: models.CountryCode,
        request: models.RefundCharge,
        idempotency_key: models.IdempotencyKey,
    ) -> models.Refund:
        """
        Refund a Charge
        https://stripe.com/docs/api/refunds
        """
        ...

    def update_stripe_dispute(
        self, request: models.UpdateStripeDispute
    ) -> models.StripeDisputeId:
        """
        Update a Dispute
        https://stripe.com/docs/api/disputes/update
        """
        ...


@tracing.track_breadcrumb(provider_name="stripe", from_kwargs={"country": "country"})
class StripeClient(StripeClientInterface):
    """
    production stripe client
    """

    client_settings: models.SettingsByCountryCode
    http_client: HTTPClient

    def __init__(
        self,
        settings_list: models.SettingsList,
        *,
        http_client: Optional[HTTPClient] = None,
    ):
        if len(settings_list) == 0:
            raise ValueError("at least one client configuration needs to be provided")
        self.client_settings = {
            settings.country: settings for settings in settings_list
        }

        self.http_client = http_client or TimedRequestsClient()

        # globally set the stripe client
        set_default_http_client(self.http_client)

    def settings_for(self, country: models.CountryCode) -> dict:
        try:
            return self.client_settings[country].client_settings
        except KeyError as err:
            raise errors.ServiceProviderException(
                f"service provider is not configured for country {country}"
            ) from err

    @tracing.track_breadcrumb(resource="token", action="create")
    def create_connected_account_token(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="customer", action="create")
    def create_customer(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="customer", action="modify")
    def update_customer(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="paymentmethod", action="create")
    def create_payment_method(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="paymentmethod", action="attach")
    def attach_payment_method(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="paymentmethod", action="detach")
    def detach_payment_method(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="paymentmethod", action="retrieve")
    def retrieve_payment_method(
        self,
        *,
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

    @tracing.track_breadcrumb(resource="paymentintent", action="create")
    def create_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CreatePaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntent:
        payment_intent = stripe.PaymentIntent.create(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_intent

    @tracing.track_breadcrumb(resource="paymentintent", action="capture")
    def capture_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CapturePaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntent:
        payment_intent = stripe.PaymentIntent.capture(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_intent

    @tracing.track_breadcrumb(resource="paymentintent", action="cancel")
    def cancel_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CancelPaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntentId:
        payment_intent = stripe.PaymentIntent.cancel(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payment_intent.id

    @tracing.track_breadcrumb(resource="refund", action="create")
    def refund_charge(
        self,
        *,
        country: models.CountryCode,
        request: models.RefundCharge,
        idempotency_key: models.IdempotencyKey,
    ) -> models.Refund:
        refund = stripe.Refund.create(
            idempotency_key=idempotency_key,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return refund

    def update_stripe_dispute(
        self, request: models.UpdateStripeDispute
    ) -> models.StripeDisputeId:
        dispute = stripe.Dispute.modify(**request.dict(skip_defaults=True))
        return dispute.id


class StripeTestClient(StripeClient):
    """
    stripe client for testing only
    includes methods that should not be called outside of tests
    (eg. credit card creation)
    """

    def create_bank_account_token(
        self,
        *,
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
        *,
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
        *,
        settings_list: models.SettingsList = None,
        max_workers: Optional[int] = None,
        client: Optional[StripeClient] = None,
        http_client: Optional[HTTPClient] = None,
    ):
        # ensure threadpool workers get the right prefix
        if client is not None:
            self.client = client
        elif settings_list is not None:
            self.client = StripeClient(settings_list, http_client=http_client)
        else:
            raise ValueError(
                "either a Stripe Client `client` or the client `settings_list` must be specified"
            )

        super().__init__(max_workers=max_workers)

    async def create_connected_account_token(
        self,
        *,
        country: models.CountryCode,
        token: models.CreateConnectedAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.TokenId:
        return await self.submit(
            self.client.create_connected_account_token,
            country=country,
            token=token,
            idempotency_key=idempotency_key,
        )

    async def create_customer(
        self,
        *,
        country: models.CountryCode,
        request: models.CreateCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.CustomerId:
        return await self.submit(
            self.client.create_customer,
            country=country,
            request=request,
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
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def create_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.CreatePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.create_payment_method,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def attach_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.AttachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.attach_payment_method,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def detach_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.DetachPaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.detach_payment_method,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def retrieve_payment_method(
        self,
        *,
        country: models.CountryCode,
        request: models.RetrievePaymentMethod,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.PaymentMethod:
        return await self.submit(
            self.client.retrieve_payment_method,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def create_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CreatePaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntent:
        return await self.submit(
            self.client.create_payment_intent,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def capture_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CapturePaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntent:
        return await self.submit(
            self.client.capture_payment_intent,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def cancel_payment_intent(
        self,
        *,
        country: models.CountryCode,
        request: models.CancelPaymentIntent,
        idempotency_key: models.IdempotencyKey,
    ) -> models.PaymentIntentId:
        return await self.submit(
            self.client.cancel_payment_intent,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def refund_charge(
        self,
        *,
        country: models.CountryCode,
        request: models.RefundCharge,
        idempotency_key: models.IdempotencyKey,
    ) -> models.Refund:
        return await self.submit(
            self.client.refund_charge,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def update_stripe_dispute(
        self, request: models.UpdateStripeDispute
    ) -> models.StripeDisputeId:
        return await self.submit(self.client.update_stripe_dispute, request)
