from typing import Optional, Tuple
from uuid import UUID

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.commons.providers.stripe.stripe_models import CustomerId
from app.commons.types import CountryCode, PgpCode
from app.payin.core.exceptions import PayerReadError, PayinErrorCode
from app.payin.core.payer.model import Payer, RawPayer
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payment_method.model import RawPaymentMethod, PaymentMethodIds
from app.payin.core.types import (
    PaymentMethodIdType,
    MixedUuidStrType,
    PayerReferenceIdType,
)


class PayerProcessorV1:
    """
    Entry of business layer which defines the workflow of v1 payers endpoint of API presentation layer.
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
        payer_reference_id: str,
        payer_reference_id_type: PayerReferenceIdType,
        email: str,
        country: CountryCode,
        description: str,
    ) -> Tuple[Payer, bool]:
        """
        create a new DoorDash payer. We will create 3 models under the hood:
            - Payer
            - PgpCustomer
            - StripeCustomer (for backward compatibility)

        :param payer_reference_id: DoorDash client identifier (consumer_id, etc.)
        :param payer_reference_id_type: Payment predefined values.
        :param email: payer email
        :param country: payer country code
        :param description: short description for the payer
        :return: Payer object
        """
        self.log.info(
            "[create_payer] started.",
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
        )

        # TODO: we should get pgp_code in different way
        pgp_code = PgpCode.STRIPE

        # step 1: lookup active payer by payer_reference_id + payer_reference_id_type, return error if payer already exists
        existing_payer = await self.payer_client.find_existing_payer(
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
        )
        if existing_payer:
            return existing_payer, True

        # step 2: create PGP customer
        pgp_customer_id: CustomerId = await self.payer_client.pgp_create_customer(
            country=country, email=email, description=description
        )

        self.log.info(
            "[create_payer] create PGP customer completed.",
            payer_reference_id=payer_reference_id,
            pgp_customer_id=pgp_customer_id,
        )

        # step 3: create Payer/PgpCustomer/StripeCustomer objects
        raw_payer: RawPayer = await self.payer_client.create_raw_payer(
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
            country=country,
            pgp_customer_resource_id=pgp_customer_id,
            pgp_code=pgp_code,
            description=description,
        )
        return raw_payer.to_payer(), False

    async def get_payer(
        self,
        payer_lookup_id: MixedUuidStrType,
        payer_reference_id_type: PayerReferenceIdType,
        force_update: bool,
    ) -> Payer:
        """
        Retrieve DoorDash payer.

        :param payer_lookup_id: either payer_id or payer_reference_id.
        :param payer_reference_id_type: payer reference id type.
        :param force_update: force update from payment provider.
        :return: Payer object
        """
        self.log.info(
            "[get_payer] started.",
            payer_lookup_id=payer_lookup_id,
            payer_reference_id_type=payer_reference_id_type,
            force_update=force_update,
        )

        raw_payer: RawPayer = await self.payer_client.get_raw_payer(
            mixed_payer_id=payer_lookup_id,
            payer_reference_id_type=payer_reference_id_type,
        )

        if force_update:
            # ensure DB record is update-to-date
            country: Optional[CountryCode] = CountryCode(raw_payer.country())
            if not country:
                raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_NOT_FOUND)
            raw_payer = await self.payer_client.force_update_payer(
                raw_payer=raw_payer, country=country
            )

        return raw_payer.to_payer()

    async def update_default_payment_method(
        self,
        payer_lookup_id: MixedUuidStrType,
        payer_reference_id_type: PayerReferenceIdType,
        payment_method_id: Optional[UUID],
        dd_stripe_card_id: Optional[str],
    ):
        """
        Update DoorDash payer's default payment method.

        :param payer_lookup_id: either payer_id or payer_reference_id.
        :param payer_reference_id_type: payer reference id type.
        :param payment_method_id: new default payment_method identity.
        :param dd_stripe_card_id: new default payment_method identity.
        :return: Payer object
        """

        # TODO: interface decision - short-term decision is to support both payment_method_id and dd_stripe_card_id
        # as external identity due to the dd_stripe_card_id is highly coupled all the way to mobile applications.
        # FIXME: will refactor payer_client.get_raw_payment_method_without_payer_auth() to remove the mix
        # type from API signature.
        mix_payment_method_id: Optional[
            MixedUuidStrType
        ] = payment_method_id if payment_method_id else dd_stripe_card_id
        if not mix_payment_method_id:
            self.log.error(
                "[update_default_payment_method] null payment_method_id and null dd_stripe_card_id."
            )
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_INVALID_DATA)

        # step 1: find Payer object to get pgp_resource_id. Exception is handled by get_payer_raw_objects()
        raw_payer: RawPayer = await self.payer_client.get_raw_payer(
            mixed_payer_id=payer_lookup_id,
            payer_reference_id_type=payer_reference_id_type,
        )
        pgp_country: Optional[str] = raw_payer.country()
        if not pgp_country:
            raise PayerReadError(error_code=PayinErrorCode.PAYER_READ_NOT_FOUND)

        # step 2: find PaymentMethod object to get pgp_resource_id.
        raw_pm: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=mix_payment_method_id,
            payment_method_id_type=(
                PaymentMethodIdType.PAYMENT_METHOD_ID
                if payment_method_id
                else PaymentMethodIdType.DD_STRIPE_CARD_ID
            ),
        )

        # step 3: call PGP/stripe api to update default payment method
        stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
            country=pgp_country,
            pgp_customer_resource_id=raw_payer.pgp_payer_resource_id,
            pgp_payment_method_resource_id=raw_pm.pgp_payment_method_resource_id,
        )

        self.log.info(
            "[update_payer] PGP update default_payment_method completed",
            payer_lookup_id=payer_lookup_id,
            payer_reference_id_type=payer_reference_id_type,
            pgp_default_payment_method_resource_id=stripe_customer.invoice_settings.default_payment_method,
        )

        # step 4: update default_payment_method in pgp_customers/stripe_customer table
        updated_raw_payer: RawPayer = await self.payer_client.update_default_payment_method(
            raw_payer=raw_payer,
            payment_method_ids=PaymentMethodIds(
                pgp_payment_method_resource_id=raw_pm.pgp_payment_method_resource_id,
                dd_stripe_card_id=raw_pm.legacy_dd_stripe_card_id,
                payment_method_id=raw_pm.payment_method_id,
            ),
        )

        return updated_raw_payer.to_payer()
