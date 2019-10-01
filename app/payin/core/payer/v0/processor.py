from typing import Optional

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.providers.stripe.stripe_models import Customer as StripeCustomer
from app.commons.runtime import runtime
from app.commons.types import CountryCode, PgpCode
from app.payin.core.exceptions import PayerReadError, PayinErrorCode
from app.payin.core.payer.model import Payer, RawPayer, PaymentGatewayProviderCustomer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import LegacyPayerInfo
from app.payin.core.payment_method.model import RawPaymentMethod
from app.payin.core.types import PayerIdType, PaymentMethodIdType


class PayerProcessorV0:
    """
    Entry of business layer which defines the workflow of v0 payers endpoint of API presentation layer.
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

    async def get_payer(
        self, legacy_payer_info: LegacyPayerInfo, force_update: Optional[bool] = False
    ):
        """
        Retrieve DoorDash payer.

        :param legacy_payer_info: legacy payer information.
        :param force_update: force update from payment provider.
        :return: Payer object
        """
        self.log.info(
            "[get_payer] started.",
            legacy_payer_info=legacy_payer_info,
            force_update=force_update,
        )

        force_retrieving = runtime.get_bool(
            "payin/feature-flags/force_retrieve_stripe_customer.bool", True
        )

        try:
            raw_payer: RawPayer = await self.payer_client.get_raw_payer(
                payer_id=legacy_payer_info.payer_id,
                payer_id_type=legacy_payer_info.payer_id_type,
                payer_type=legacy_payer_info.payer_type,
            )
        except PayerReadError as e:
            if (
                e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND
                and force_update
                and force_retrieving
                and legacy_payer_info.payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID
            ):
                pgp_customer: StripeCustomer = await self.payer_client.pgp_get_customer(
                    pgp_customer_id=str(legacy_payer_info.payer_id),
                    country=CountryCode(legacy_payer_info.country),
                )

                pgp_payment_method_resource_id: Optional[str] = None
                if (
                    pgp_customer.invoice_settings
                    and pgp_customer.invoice_settings.default_payment_method
                ):
                    pgp_payment_method_resource_id = (
                        pgp_customer.invoice_settings.default_payment_method
                    )
                if not pgp_payment_method_resource_id:
                    pgp_payment_method_resource_id = pgp_customer.default_source

                provider_customer = PaymentGatewayProviderCustomer(
                    payment_provider=PgpCode.STRIPE,
                    payment_provider_customer_id=pgp_customer.id,
                    default_payment_method_id=pgp_payment_method_resource_id,
                )

                return Payer(
                    country=legacy_payer_info.country,
                    created_at=pgp_customer.created,
                    description=pgp_customer.description,
                    payment_gateway_provider_customers=[provider_customer],
                )
            else:
                raise e

        # if force_update and raw_payer:
        if force_update:
            # ensure DB record is update-to-date
            country: Optional[CountryCode] = CountryCode(raw_payer.country()) or (
                legacy_payer_info.country if legacy_payer_info else None
            )
            if country:
                raw_payer = await self.payer_client.force_update_payer(
                    raw_payer=raw_payer, country=country
                )

        return raw_payer.to_payer()

    async def update_default_payment_method(
        self, legacy_payer_info: LegacyPayerInfo, dd_stripe_card_id: str
    ):
        """
        Update DoorDash payer's default payment method.

        :param legacy_payer_info: legacy payer information.
        :param dd_stripe_card_id: new default payment_method identity. It's serial id from maindb.stripe_card table.
        :return: Payer object
        """

        # step 1: find PaymentMethod object to get pgp_resource_id.
        raw_pm: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=dd_stripe_card_id,
            payment_method_id_type=PaymentMethodIdType.DD_STRIPE_CARD_ID,
        )

        # step 2: find Payer object to get pgp_resource_id. Exception is handled by get_payer_raw_objects()
        try:
            raw_payer: RawPayer = await self.payer_client.get_raw_payer(
                payer_id=legacy_payer_info.payer_id,
                payer_id_type=legacy_payer_info.payer_id_type,
                payer_type=legacy_payer_info.payer_type,
            )
        except PayerReadError as e:
            if (
                e.error_code == PayinErrorCode.PAYER_READ_NOT_FOUND
                and legacy_payer_info.payer_id_type == PayerIdType.STRIPE_CUSTOMER_ID
            ):
                # DSJ consumer, there's no record in payers table and pgp_customers table.
                stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
                    country=legacy_payer_info.country,
                    pgp_customer_resource_id=legacy_payer_info.payer_id,
                    pgp_payment_method_resource_id=raw_pm.pgp_payment_method_resource_id,
                )

                provider_customer = PaymentGatewayProviderCustomer(
                    payment_provider=PgpCode.STRIPE,
                    payment_provider_customer_id=stripe_customer.id,
                    default_payment_method_id=stripe_customer.invoice_settings.default_payment_method,
                )
                return Payer(
                    country=legacy_payer_info.country,
                    payment_gateway_provider_customers=[provider_customer],
                )

        # step 3: call PGP/stripe api to update default payment method
        pgp_customer_resource_id: str = raw_payer.pgp_payer_resource_id
        stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
            country=legacy_payer_info.country,
            pgp_customer_resource_id=pgp_customer_resource_id,
            pgp_payment_method_resource_id=raw_pm.pgp_payment_method_resource_id,
        )

        self.log.info(
            "[update_payer] PGP update default_payment_method completed",
            payer_id=legacy_payer_info.payer_id,
            payer_id_type=legacy_payer_info.payer_id_type,
            pgp_default_payment_method_resource_id=stripe_customer.invoice_settings.default_payment_method,
        )

        # step 4: update default_payment_method in pgp_customers/stripe_customer table
        updated_raw_payer: RawPayer = await self.payer_client.update_default_payment_method(
            raw_payer=raw_payer,
            pgp_default_payment_method_id=raw_pm.pgp_payment_method_resource_id,
            payer_id=legacy_payer_info.payer_id,
            payer_id_type=legacy_payer_info.payer_id_type,
        )

        return updated_raw_payer.to_payer()
