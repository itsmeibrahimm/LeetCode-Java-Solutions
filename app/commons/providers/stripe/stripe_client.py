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
from app.commons.providers.stripe.stripe_models import CreateAccountTokenRequest
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
    def retrieve_customer(
        self,
        *,
        country: models.CountryCode,
        request: models.RetrieveCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.Customer:
        """
        Create a new Stripe Customer
        https://stripe.com/docs/api/customers/retrieve
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

    @abc.abstractmethod
    def update_stripe_dispute(
        self, request: models.UpdateDispute
    ) -> models.StripeDisputeId:
        """
        Update a Dispute
        https://stripe.com/docs/api/disputes/update
        """
        ...

    @abc.abstractmethod
    def create_transfer(
        self,
        *,
        country: models.CountryCode,
        currency: models.Currency,
        destination: models.Destination,
        amount: models.Amount,
        request: models.CreateTransfer,
    ) -> models.Transfer:
        """
        Create a Transfer
        https://stripe.com/docs/api/transfers/create
        """
        ...

    @abc.abstractmethod
    def create_payout(
        self,
        *,
        country: models.CountryCode,
        currency: models.Currency,
        amount: models.Amount,
        request: models.CreatePayout,
    ) -> models.Payout:
        """
        Create a Payout
        https://stripe.com/docs/api/payouts/create
        """
        ...

    @abc.abstractmethod
    def create_transfer_for_payout(
        self,
        *,
        currency: models.Currency,
        amount: models.Amount,
        statement_descriptor: models.StatementDescriptor,
        stripe_account_id: models.StripeAccountId,
        country: models.CountryCode,
        metadata: models.Metadata,
        request: models.CreatePayout,
    ) -> models.Payout:
        """
        Create a Transfer Stripe api version 2016-02-29
        https://stripe.com/docs/api/transfers/create
        """
        ...

    @abc.abstractmethod
    def retrieve_payout(
        self, *, country: models.CountryCode, request: models.RetrievePayout
    ) -> models.Payout:
        """
        Retrieve a Payout
        https://stripe.com/docs/api/payouts/retrieve
        """
        ...

    @abc.abstractmethod
    def cancel_payout(
        self, *, request: models.CancelPayout, country: models.CountryCode
    ) -> models.Payout:
        """
        Cancel a Payout
        https://stripe.com/docs/api/payouts/cancel
        """
        ...

    @abc.abstractmethod
    def retrieve_balance(
        self, *, stripe_account: models.StripeAccountId, country: models.CountryCode
    ) -> models.Balance:
        """
        Retrieve Balance
        https://stripe.com/docs/api/balance/balance_retrieve
        """

    @abc.abstractmethod
    def create_account_token(
        self, request: models.CreateAccountTokenRequest
    ) -> models.AccountToken:
        """
        Create an Account Token
        https://stripe.com/docs/api/tokens/create_account
        """

    @abc.abstractmethod
    def create_stripe_account(
        self, request: models.CreateAccountRequest
    ) -> models.Account:
        """
        Create an Account
        https://stripe.com/docs/api/accounts/create
        """


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
        self.stripe_client_settings = {
            settings.country: settings for settings in settings_list
        }

        self.http_client = http_client or TimedRequestsClient()

        # globally set the stripe client
        set_default_http_client(self.http_client)

    def settings_for(self, country: models.CountryCode) -> dict:
        try:
            return self.stripe_client_settings[country].client_settings
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

    @tracing.track_breadcrumb(resource="customer", action="retrieve")
    def retrieve_customer(
        self,
        *,
        country: models.CountryCode,
        request: models.RetrieveCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.Customer:
        customer = stripe.Customer.retrieve(
            **self.settings_for(country), **request.dict(skip_defaults=True)
        )
        return customer

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

    @tracing.track_breadcrumb(resource="stripedispute", action="modify")
    def update_stripe_dispute(
        self, request: models.UpdateDispute
    ) -> models.StripeDisputeId:
        dispute = stripe.Dispute.modify(**request.dict(skip_defaults=True))
        return dispute.id

    @tracing.track_breadcrumb(resource="transfer", action="create")
    def create_transfer(
        self,
        *,
        country: models.CountryCode,
        currency: models.Currency,
        destination: models.Destination,
        amount: models.Amount,
        request: models.CreateTransfer,
    ) -> models.Transfer:
        transfer = stripe.Transfer.create(
            currency=currency,
            destination=destination,
            amount=amount,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return transfer

    @tracing.track_breadcrumb(resource="payout", action="create")
    def create_payout(
        self,
        *,
        country: models.CountryCode,
        currency: models.Currency,
        amount: models.Amount,
        stripe_account: models.StripeAccountId,
        request: models.CreatePayout,
    ) -> models.Payout:
        payout = stripe.Payout.create(
            currency=currency,
            amount=amount,
            stripe_account=stripe_account,
            **self.settings_for(country),
            **request.dict(skip_defaults=True),
        )
        return payout

    @tracing.track_breadcrumb(resource="transfer", action="create")
    def create_transfer_for_payout(
        self,
        *,
        currency: models.Currency,
        amount: models.Amount,
        statement_descriptor: models.StatementDescriptor,
        stripe_account_id: models.StripeAccountId,
        country: models.CountryCode,
        metadata: models.Metadata,
        request: models.CreatePayout,
    ) -> models.Payout:
        # we use 2016 stripe api create_transfer to payout to bank account, since in current version it requires
        # external_account stripe_id which we did not save in our db
        payout = stripe.Transfer.create(
            currency=currency,
            amount=amount,
            stripe_version="2016-02-29",
            country=country,
            recipient="self",
            statement_descriptor=statement_descriptor,
            stripe_account_id=stripe_account_id,
            metadata=metadata,
            **request.dict(skip_defaults=True),
        )
        return payout

    @tracing.track_breadcrumb(resource="payout", action="retrieve")
    def retrieve_payout(
        self, *, country: models.CountryCode, request: models.RetrievePayout
    ) -> models.Payout:
        payout = stripe.Payout.retrieve(
            **self.settings_for(country), **request.dict(skip_defaults=True)
        )
        return payout

    @tracing.track_breadcrumb(resource="payout", action="cancel")
    def cancel_payout(
        self, *, request: models.CancelPayout, country: models.CountryCode
    ) -> models.Payout:
        payout = stripe.Payout.cancel(
            **self.settings_for(country), **request.dict(skip_defaults=True)
        )
        return payout

    @tracing.track_breadcrumb(resource="balance", action="retrieve")
    def retrieve_balance(
        self, *, stripe_account: models.StripeAccountId, country: models.CountryCode
    ) -> models.Balance:
        balance = stripe.Balance.retrieve(
            stripe_account=stripe_account, **self.settings_for(country)
        )
        return balance

    @tracing.track_breadcrumb(resource="token", action="create")
    def create_account_token(
        self, *, request: CreateAccountTokenRequest
    ) -> models.AccountToken:
        account_token = stripe.Token.create(
            account=request.account.dict(), **self.settings_for(request.country)
        )
        return account_token

    @tracing.track_breadcrumb(resource="account", action="create")
    def create_stripe_account(
        self, *, request: models.CreateAccountRequest
    ) -> models.Account:
        account = stripe.Account.create(
            type=request.type,
            account_token=request.account_token,
            requested_capabilities=request.requested_capabilities,
            **self.settings_for(request.country),
        )
        return account


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


class StripeAsyncClient:
    executor_pool: ThreadPoolHelper
    stripe_client: StripeClient
    commando: bool

    def __init__(
        self,
        executor_pool: ThreadPoolHelper,
        stripe_client: StripeClient,
        commando: bool = False,
    ):
        self.executor_pool = executor_pool
        self.stripe_client = stripe_client
        self.commando = commando

    async def create_connected_account_token(
        self,
        *,
        country: models.CountryCode,
        token: models.CreateConnectedAccountToken,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.TokenId:
        return await self.executor_pool.submit(
            self.stripe_client.create_connected_account_token,
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
        return await self.executor_pool.submit(
            self.stripe_client.create_customer,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def retrieve_customer(
        self,
        *,
        country: models.CountryCode,
        request: models.RetrieveCustomer,
        idempotency_key: models.IdempotencyKey = None,
    ) -> models.Customer:
        return await self.executor_pool.submit(
            self.stripe_client.retrieve_customer,
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
        return await self.executor_pool.submit(
            self.stripe_client.update_customer,
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
        return await self.executor_pool.submit(
            self.stripe_client.create_payment_method,
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
        return await self.executor_pool.submit(
            self.stripe_client.attach_payment_method,
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
        return await self.executor_pool.submit(
            self.stripe_client.detach_payment_method,
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
        return await self.executor_pool.submit(
            self.stripe_client.retrieve_payment_method,
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
        return await self.executor_pool.submit(
            self.stripe_client.create_payment_intent,
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
        return await self.executor_pool.submit(
            self.stripe_client.capture_payment_intent,
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
        return await self.executor_pool.submit(
            self.stripe_client.cancel_payment_intent,
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
        return await self.executor_pool.submit(
            self.stripe_client.refund_charge,
            country=country,
            request=request,
            idempotency_key=idempotency_key,
        )

    async def update_dispute(
        self, country: models.CountryCode, request: models.UpdateDispute
    ) -> models.StripeDisputeId:
        return await self.executor_pool.submit(
            self.stripe_client.update_stripe_dispute, request
        )

    async def create_transfer(
        self,
        *,
        country: models.CountryCode,
        currency: models.Currency,
        destination: models.Destination,
        amount: models.Amount,
        request: models.CreateTransfer,
    ) -> models.Transfer:
        return await self.executor_pool.submit(
            self.stripe_client.create_transfer,
            country=country,
            currency=currency,
            destination=destination,
            amount=amount,
            request=request,
        )

    async def create_payout(
        self,
        *,
        country: models.CountryCode,
        currency: models.Currency,
        amount: models.Amount,
        request: models.CreatePayout,
    ) -> models.Payout:
        return await self.executor_pool.submit(
            self.stripe_client.create_payout,
            currency=currency,
            amount=amount,
            country=country,
            request=request,
        )

    async def create_transfer_for_payout(
        self,
        *,
        currency: models.Currency,
        amount: models.Amount,
        statement_descriptor: models.StatementDescriptor,
        stripe_account_id: models.StripeAccountId,
        country: models.CountryCode,
        metadata: models.Metadata,
        request: models.CreatePayout,
    ) -> models.Payout:
        # we use 2016 stripe api create_transfer to payout to bank account, since in current venison it requires
        # external_account stripe_id which we did not save in our db
        return await self.executor_pool.submit(
            self.stripe_client.create_transfer,
            currency=currency,
            amount=amount,
            country=country,
            recipient="self",
            statement_descriptor=statement_descriptor,
            stripe_account_id=stripe_account_id,
            metadata=metadata,
            request=request,
        )

    async def retrieve_payout(
        self, *, request: models.RetrievePayout, country: models.CountryCode
    ) -> models.Payout:
        return await self.executor_pool.submit(
            self.stripe_client.retrieve_payout, request=request, country=country
        )

    async def cancel_payout(
        self, *, request: models.CancelPayout, country: models.CountryCode
    ) -> models.Payout:
        return await self.executor_pool.submit(
            self.stripe_client.cancel_payout, request=request, country=country
        )

    async def retrieve_balance(
        self, *, stripe_account: models.StripeAccountId, country: models.CountryCode
    ) -> models.Balance:
        return await self.executor_pool.submit(
            self.stripe_client.retrieve_balance,
            stripe_account=stripe_account,
            country=country,
        )

    async def create_account_token(
        self, *, request: models.CreateAccountTokenRequest
    ) -> models.AccountToken:
        return await self.executor_pool.submit(
            self.stripe_client.create_account_token, request=request
        )

    async def create_stripe_account(
        self, *, request: models.CreateAccountRequest
    ) -> models.Account:
        return await self.executor_pool.submit(
            self.stripe_client.create_stripe_account, request=request
        )
