from typing import Optional

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.providers.stripe.stripe_models import (
    CustomerId,
    Customer as StripeCustomer,
)
from app.commons.runtime import runtime
from app.commons.types import CountryCode
from app.commons.utils.types import PaymentProvider
from app.payin.core.exceptions import PayerReadError, PayinErrorCode
from app.payin.core.payer.model import Payer, RawPayer, PaymentGatewayProviderCustomer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.types import PayerIdType, MixedUuidStrType, PaymentMethodIdType


class PayerProcessor:
    """
    Entry of business layer which defines the workflow of each endpoint of API presentation layer.
    """

    # prevent circular dependency
    from app.payin.core.payment_method.processor import PaymentMethodClient

    def __init__(
        self,
        payment_method_client: PaymentMethodClient = Depends(PaymentMethodClient),
        payer_client: PayerClient = Depends(PayerClient),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.payer_client = payer_client
        self.log = log
        self.payment_method_client = payment_method_client

    async def create_payer(
        self,
        dd_payer_id: str,
        payer_type: str,
        email: str,
        country: str,
        description: str,
    ) -> Payer:
        """
        create a new DoorDash payer. We will create 3 models under the hood:
            - Payer
            - PgpCustomer
            - StripeCustomer (for backward compatibility)

        :param dd_payer_id: DoorDash client identifier (consumer_id, etc.)
        :param payer_type: Identify the owner type
        :param email: payer email
        :param country: payer country code
        :param description: short description for the payer
        :return: Payer object
        """
        self.log.info(
            "[create_payer] started.", dd_payer_id=dd_payer_id, payer_type=payer_type
        )

        # TODO: we should get pgp_code in different way
        pgp_code = PaymentProvider.STRIPE

        # step 1: lookup active payer by dd_payer_id + payer_type, return error if payer already exists
        await self.payer_client.has_existing_payer(
            dd_payer_id=dd_payer_id, payer_type=payer_type
        )

        # step 2: create PGP customer
        pgp_customer_id: CustomerId = await self.payer_client.pgp_create_customer(
            country=country, email=email, description=description
        )

        self.log.info(
            f"[create_payer_impl][{dd_payer_id}] create PGP customer completed. id:[{pgp_customer_id}]"
        )

        # step 3: create Payer/PgpCustomer/StripeCustomer objects
        raw_payer: RawPayer = await self.payer_client.create_raw_payer(
            dd_payer_id=dd_payer_id,
            payer_type=payer_type,
            country=country,
            pgp_customer_id=pgp_customer_id,
            pgp_code=pgp_code,
            description=description,
        )
        return raw_payer.to_payer()

    async def get_payer(
        self,
        payer_id: MixedUuidStrType,
        payer_type: Optional[str],
        payer_id_type: Optional[str] = None,
        country: Optional[CountryCode] = CountryCode.US,
        force_update: Optional[bool] = False,
    ):
        """
        Retrieve DoorDash payer

        :param payer_id: payer unique id.
        :param payer_type: Identify the owner type. This is for backward compatibility.
               Caller can ignore it for new consumer who is onboard from
               new payer APIs.
        :param payer_id_type: [string] identify the type of payer_id. Valid values include "dd_payer_id",
               "stripe_customer_id", "stripe_customer_serial_id" (default is "dd_payer_id")
        :return: Payer object
        """
        self.log.info(
            "[get_payer] started.",
            payer_id=payer_id,
            payer_id_type=payer_id_type,
            force_update=force_update,
        )

        force_retrieving = runtime.get_bool(
            "feature-flags/payin/force_retrieve_stripe_customer.bool", True
        )
        try:
            raw_payer: RawPayer = await self.payer_client.get_raw_payer(
                payer_id=payer_id, payer_id_type=payer_id_type, payer_type=payer_type
            )
        except PayerReadError as e:
            if (
                e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND
                and force_update
                and force_retrieving
                and payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID
            ):
                pgp_customer: StripeCustomer = await self.payer_client.pgp_get_customer(
                    pgp_customer_id=str(payer_id), country=CountryCode(country)
                )

                default_pm_id: Optional[str] = None
                if (
                    pgp_customer.invoice_settings
                    and pgp_customer.invoice_settings.default_payment_method
                ):
                    default_pm_id = pgp_customer.invoice_settings.default_payment_method
                if not default_pm_id:
                    default_pm_id = pgp_customer.default_source

                provider_customer = PaymentGatewayProviderCustomer(
                    payment_provider=PaymentProvider.STRIPE,
                    payment_provider_customer_id=pgp_customer.id,
                    default_payment_method_id=default_pm_id,
                )

                return Payer(
                    country=country,
                    created_at=pgp_customer.created,
                    description=pgp_customer.description,
                    payment_gateway_provider_customers=[provider_customer],
                )
            else:
                raise e

        if force_update:
            # ensure DB record is update-to-date
            raw_payer = await self.payer_client.force_update_payer(
                raw_payer=raw_payer, country=country
            )

        return raw_payer.to_payer()

    async def update_payer(
        self,
        payer_id: MixedUuidStrType,
        default_payment_method_id: str,
        country: Optional[CountryCode] = CountryCode.US,
        payer_id_type: Optional[PayerIdType] = None,
        payer_type: Optional[str] = None,
        payment_method_id_type: Optional[PaymentMethodIdType] = None,
    ):
        """
        Update DoorDash payer's default payment method.

        :param country:
        :param payer_id: payer unique id.
        :param default_payment_method_id: new default payment_method identity.
        :param payer_id_type: Identify the owner type. This is for backward compatibility.
                              Caller can ignore it for new consumer who is onboard from
                              new payer APIs.
        :param payer_type:
        :param payment_method_id_type:
        :param payer_client: Utility client that manipulates payer objects
        :return: Payer object
        """
        # step 1: find Payer object to get pgp_resource_id. Exception is handled by get_payer_raw_objects()
        raw_payer: RawPayer = await self.payer_client.get_raw_payer(
            payer_id=payer_id, payer_type=payer_type
        )
        pgp_country: Optional[
            str
        ] = raw_payer.country() if raw_payer.country() else country

        # step 2: find PaymentMethod object to get pgp_resource_id.
        raw_pm: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=default_payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )

        # step 3: call PGP/stripe api to update default payment method
        pgp_customer_id: Optional[str] = raw_payer.pgp_customer_id()
        if pgp_customer_id:
            stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
                country=pgp_country,
                pgp_customer_id=pgp_customer_id,
                default_payment_method_id=raw_pm.pgp_payment_method_id(),
            )

            self.log.info(
                f"[update_payer_impl] PGP update default_payment_method completed",
                payer_id=payer_id,
                payer_id_type=payer_id_type,
                default_payment_method=stripe_customer.invoice_settings.default_payment_method,
            )

        # step 4: update default_payment_method in pgp_customers/stripe_customer table
        updated_raw_payer: RawPayer = await self.payer_client.update_payer_default_payment_method(
            raw_payer=raw_payer,
            pgp_default_payment_method_id=raw_pm.pgp_payment_method_id(),
            payer_id=payer_id,
            payer_type=payer_type,
            payer_id_type=payer_id_type,
        )

        return updated_raw_payer.to_payer()
