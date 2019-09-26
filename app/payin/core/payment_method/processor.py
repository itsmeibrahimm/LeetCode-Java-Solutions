from typing import Optional
from uuid import UUID

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req
from app.commons.providers.stripe.stripe_models import (
    PaymentMethod as StripePaymentMethod,
)
from app.commons.types import CountryCode
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PaymentMethodCreateError,
    PayinErrorCode,
    PaymentMethodReadError,
    PayerReadError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payer.types import PayerType
from app.payin.core.payment_method.model import (
    PaymentMethod,
    RawPaymentMethod,
    PaymentMethodList,
)
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.payment_method.types import SortKey, LegacyPaymentMethodInfo
from app.payin.core.types import PaymentMethodIdType, PayerIdType


class PaymentMethodProcessor:
    """
    Entry of business layer which defines the workflow of each endpoint of API presentation layer.
    """

    # prevent circular dependency
    from app.payin.core.payer.processor import PayerClient

    def __init__(
        self,
        log: BoundLogger = Depends(get_logger_from_req),
        app_ctxt: AppContext = Depends(get_global_app_context),
        payment_method_client=Depends(PaymentMethodClient),
        payer_client=Depends(PayerClient),
    ):
        self.log = log
        self.app_ctxt = app_ctxt
        self.payment_method_client = payment_method_client
        self.payer_client = payer_client

    async def create_payment_method(
        self,
        pgp_code: str,
        token: str,
        set_default: Optional[bool] = False,
        is_scanned: Optional[bool] = False,
        payer_id: UUID = None,
        legacy_payment_method_info: Optional[LegacyPaymentMethodInfo] = None,
    ) -> PaymentMethod:
        """
        Create payment method and attach to payer.

        :param pgp_code: payment gateway provider code (eg. "stripe")
        :param token: payment provider authorized one-time payment method token.
        :param set_default: set the new payment method as default.
        :param is_scanned: for fraud usage.
        :param payer_id: DoorDash payer id.
        :param legacy_payment_method_info: legacy payment method info.
        :return: PaymentMethod object
        """

        pgp_customer_res_id: Optional[str] = None
        pgp_country: Optional[str] = None
        dd_consumer_id: Optional[str] = None
        dd_stripe_customer_id: Optional[str] = None
        payer_type: Optional[str] = None
        raw_payer: Optional[RawPayer] = None

        # step 1: lookup pgp_customer_resource_id and country information
        if payer_id:
            raw_payer = await self.payer_client.get_raw_payer(
                payer_id=payer_id, payer_id_type=PayerIdType.PAYER_ID
            )
            if raw_payer and raw_payer.payer_entity:
                pgp_country = raw_payer.country()
                pgp_customer_res_id = raw_payer.pgp_payer_resource_id
                payer_type = raw_payer.payer_entity.payer_type
                if payer_type == PayerType.MARKETPLACE:
                    dd_consumer_id = raw_payer.payer_entity.dd_payer_id
                else:
                    dd_stripe_customer_id = (
                        str(raw_payer.stripe_customer_entity.id)
                        if raw_payer.stripe_customer_entity
                        else None
                    )
        elif legacy_payment_method_info:  # v0 path with legacy information
            try:
                raw_payer = await self.payer_client.get_raw_payer(
                    payer_id=legacy_payment_method_info.stripe_customer_id,
                    payer_id_type=PayerIdType.STRIPE_CUSTOMER_ID,
                    payer_type=payer_type,
                )
            except PayerReadError:
                self.log.warn(
                    "[create_payment_method] can't find raw_payer. wont update default_source in DB"
                )
            pgp_country = legacy_payment_method_info.country
            pgp_customer_res_id = legacy_payment_method_info.stripe_customer_id
            payer_type = legacy_payment_method_info.payer_type
            dd_consumer_id = legacy_payment_method_info.dd_consumer_id
            dd_stripe_customer_id = legacy_payment_method_info.dd_stripe_customer_id
        else:
            self.log.error("[create_payment_method] invalid input. must provide id")
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT,
                retryable=False,
            )

        if not pgp_customer_res_id:
            self.log.info(
                "[create_payment_method] can't find pgp_customer_resource_id",
                payer_id=payer_id,
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT,
                retryable=False,
            )

        # TODO: perform Payer's lazy creation

        # step 2: create PGP payment_method
        stripe_payment_method: StripePaymentMethod = await self.payment_method_client.pgp_create_payment_method(
            token=token, country=pgp_country
        )
        self.log.info(
            "[create_payment_method] create stripe payment_method completed",
            payer_id=payer_id,
            pgp_payment_method_res_id=stripe_payment_method.id,
        )

        # step 3: de-dup same payment_method by card fingerprint
        try:
            exist_pm: RawPaymentMethod = await self.payment_method_client.get_duplicate_payment_method(
                stripe_payment_method=stripe_payment_method,
                payer_type=payer_type,
                pgp_customer_resource_id=pgp_customer_res_id,
                dd_consumer_id=dd_consumer_id,
                dd_stripe_customer_id=dd_stripe_customer_id,
            )
        except PaymentMethodReadError:
            pass
        else:
            self.log.info(
                "[create_payment_method] duplicate card is found. return the existing one",
                dd_consumer_id=dd_consumer_id,
                pgp_payment_method_res_id=stripe_payment_method.id,
            )
            return exist_pm.to_payment_method()

        # step 4: attach PGP payment_method
        attach_stripe_payment_method: StripePaymentMethod = await self.payment_method_client.pgp_attach_payment_method(
            pgp_payment_method_res_id=stripe_payment_method.id,
            pgp_customer_id=pgp_customer_res_id,
            country=pgp_country,
        )
        self.log.info(
            "[create_payment_method] attach stripe payment_method completed",
            payer_id=payer_id,
            pgp_customer_res_id=pgp_customer_res_id,
            pgp_payment_method_res_id=attach_stripe_payment_method.id,
        )

        # step 5: crete pgp_payment_method and stripe_card objects
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.create_raw_payment_method(
            payment_method_id=generate_object_uuid(),
            pgp_code=pgp_code,
            stripe_payment_method=attach_stripe_payment_method,
            payer_id=payer_id,
            dd_consumer_id=dd_consumer_id,
            dd_stripe_customer_id=dd_stripe_customer_id,
            is_scanned=is_scanned,
        )

        # step 6: set as default payment_method
        if set_default:
            stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
                country=pgp_country,
                pgp_customer_id=pgp_customer_res_id,
                default_payment_method_id=attach_stripe_payment_method.id,
            )

            self.log.info(
                f"[create_payment_method] PGP update default_payment_method completed",
                payer_id=payer_id,
                default_payment_method=stripe_customer.invoice_settings.default_payment_method,
            )

            if raw_payer:
                await self.payer_client.update_payer_default_payment_method(
                    raw_payer=raw_payer,
                    pgp_default_payment_method_id=attach_stripe_payment_method.id,
                    payer_id=(payer_id or dd_consumer_id),
                    payer_id_type=(
                        PayerIdType.PAYER_ID if payer_id else PayerIdType.DD_CONSUMER_ID
                    ),
                )

        return raw_payment_method.to_payment_method()

    async def get_payment_method(
        self,
        payment_method_id: str,
        payment_method_id_type: PaymentMethodIdType = None,
        country: Optional[str] = None,
        force_update: Optional[bool] = False,
    ) -> PaymentMethod:
        """
        Get payment method by payment_method_id

        :param payment_method_id: DoorDash payment method id.
        :param payment_method_id_type: type of payment method.
        :param country: country only used for v0 legacy path.
        :param force_update: force update from Payment provider.
        :return: PaymentMethod object
        """

        # step 1: retrieve data from DB
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )

        # TODO: step 2: if force_update is true, we should retrieve the payment_method from GPG

        return raw_payment_method.to_payment_method()

    async def list_payment_methods(
        self,
        payer_id: str,
        payer_id_type: str = None,
        country: Optional[CountryCode] = CountryCode.US,
        active_only: bool = False,
        sort_by: SortKey = SortKey.CREATED_AT,
        force_update: bool = None,
    ) -> PaymentMethodList:
        ...

    async def delete_payment_method(
        self,
        payment_method_id: str,
        payment_method_id_type: Optional[str] = None,
        country: Optional[CountryCode] = CountryCode.US,
    ) -> PaymentMethod:
        """
        Detach a payment method.

        :param payment_method_id: DoorDash payment method id.
        :param payment_method_id_type: type of payment method.
        :param country: country only used for v0 legacy path.
        :param force_update: force update from Payment provider.
        :return: PaymentMethod object
        """

        # step 1: find payment_method.
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )
        pgp_payment_method_id: str = raw_payment_method.pgp_payment_method_resource_id

        # step 2: find payer for country information
        raw_payer: Optional[RawPayer] = None
        if raw_payment_method.payer_id():
            raw_payer = await self.payer_client.get_raw_payer(
                payer_id=raw_payment_method.payer_id()
            )

        # step 3: detach PGP payment method
        country_code: Optional[str] = raw_payer.country() if raw_payer else country
        await self.payment_method_client.pgp_detach_payment_method(
            pgp_payment_method_id=pgp_payment_method_id, country=country_code
        )

        # step 4: update pgp_payment_method.detached_at
        updated_raw_pm: RawPaymentMethod = await self.payment_method_client.detach_raw_payment_method(
            pgp_payment_method_id=pgp_payment_method_id,
            raw_payment_method=raw_payment_method,
        )

        # step 5: update payer and pgp_customers / stripe_customer to remove the default_payment_method.
        # No need to cleanup if it’s DSJ marketplace consumer because it's maintained in maindb_consumer by cx.
        # we dont automatically update the new default payment method for payer.
        if raw_payer:
            # force update for now to cover existing Cx with default_source.
            await self.payer_client.force_update_payer(
                raw_payer=raw_payer, country=country
            )

        return updated_raw_pm.to_payment_method()
