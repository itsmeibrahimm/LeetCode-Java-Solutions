from typing import Optional, List, Tuple
from uuid import UUID

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req
from app.commons.providers.stripe.stripe_models import (
    PaymentMethod as StripePaymentMethod,
)
from app.commons.runtime import runtime
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.legacy_utils import payer_type_to_payer_reference_id_type
from app.commons.utils.uuid import generate_object_uuid
from app.payin.core.exceptions import (
    PaymentMethodCreateError,
    PayinErrorCode,
    PaymentMethodReadError,
    PayerReadError,
    PaymentMethodListError,
)
from app.payin.core.payer.model import RawPayer
from app.payin.core.payment_method.model import (
    PaymentMethod,
    RawPaymentMethod,
    PaymentMethodList,
    PaymentMethodIds,
)
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.payment_method.types import (
    PaymentMethodSortKey,
    LegacyPaymentMethodInfo,
)
from app.payin.core.types import (
    PaymentMethodIdType,
    PayerReferenceIdType,
    MixedUuidStrType,
)
from app.payin.repository.payer_repo import PayerDbEntity


class PaymentMethodProcessor:
    """
    Entry of business layer which defines the workflow of each endpoint of API presentation layer.
    We upgrade from stripe source API to stripe payment method API, here is the summary of compatibility:
    1) create and attach pm_1
    2) create and attach pm_2
    3) set pm_1 as d_p_m
    4) detach pm_1 —> customer.invoice_setting[default_payment_method] is reset by stripe automatically
    5) create and attach card source card_1 —> card_1 becomes default_source by stripe automatically (stripe will also
       trigger an event about " a card payment method was attached to customer xxx")
    6) create and attach card source card_2
    7) set card_2 as default_payment_method —> stripe update customer.invoice_setting[default_payment_method] to card_2
    8) set pm_2 as default_source —> stripe rejects the request
    9) set card_1 as default_source —> customer.default_source = card_1
       and customer.invoice_setting[default_payment_method] still card_2
    10) detach pm_2 —> nothing changed
    11) delete card_2 —> customer.invoice_setting[default_payment_method]=None
        and card_1 becomes default on Stripe Dashboard
    12) create and attach source card_3
    13) delete card_1 —> card_3 becomes new default by stripe automatically
    14) create card 4
    15) detach card_1 with payment_method api —> card_4 becomes new default by stripe automatically.
        receive both "source deletion" event and "payment method detach" event
    """

    # prevent circular dependency
    from app.payin.core.payer.payer_client import PayerClient

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
        pgp_code: PgpCode,
        token: str,
        set_default: bool,
        is_scanned: bool,
        is_active: bool,
        payer_lookup_id: Optional[MixedUuidStrType] = None,
        payer_lookup_id_type: Optional[PayerReferenceIdType] = None,
        legacy_payment_method_info: Optional[LegacyPaymentMethodInfo] = None,
    ) -> Tuple[RawPaymentMethod, bool]:
        """
        Create payment method and attach to payer.

        :param pgp_code: payment gateway provider code (eg. "stripe")
        :param token: payment provider authorized one-time payment method token.
        :param set_default: set the new payment method as default.
        :param is_scanned: for fraud usage.
        :param is_active: mark as active or not. For fraud usage.
        :param payer_lookup_id: DoorDash payer_lookup_id id.
        :param payer_lookup_id_type: DoorDash payer_reference_id_type id.
        :param legacy_payment_method_info: legacy payment method info.
        :return: RawPaymentMethod object
        """

        pgp_customer_res_id: Optional[str] = None
        pgp_country: Optional[str] = None
        dd_consumer_id: Optional[str] = None
        legacy_dd_stripe_customer_id: Optional[str] = None
        payer_reference_id_type: Optional[str] = None
        raw_payer: Optional[RawPayer] = None

        # step 1: lookup pgp_customer_resource_id and country information
        if payer_lookup_id and payer_lookup_id_type:
            raw_payer = await self.payer_client.get_raw_payer(
                mixed_payer_id=payer_lookup_id,
                payer_reference_id_type=payer_lookup_id_type,
            )
            if raw_payer and raw_payer.payer_entity:
                pgp_country = raw_payer.country()
                pgp_customer_res_id = raw_payer.pgp_payer_resource_id
                payer_reference_id_type = payer_lookup_id_type
                if payer_reference_id_type == PayerReferenceIdType.DD_CONSUMER_ID:
                    dd_consumer_id = raw_payer.payer_entity.payer_reference_id
                else:
                    legacy_dd_stripe_customer_id = (
                        str(raw_payer.stripe_customer_entity.id)
                        if raw_payer.stripe_customer_entity
                        else None
                    )
        elif legacy_payment_method_info:  # v0 path with legacy information
            try:
                raw_payer = await self.payer_client.get_raw_payer(
                    mixed_payer_id=legacy_payment_method_info.stripe_customer_id,
                    payer_reference_id_type=PayerReferenceIdType.STRIPE_CUSTOMER_ID,
                )
            except PayerReadError:
                self.log.warn(
                    "[create_payment_method] can't find raw_payer. wont update default_source in DB"
                )
            pgp_country = legacy_payment_method_info.country
            pgp_customer_res_id = legacy_payment_method_info.stripe_customer_id
            payer_reference_id_type = payer_type_to_payer_reference_id_type(
                legacy_payment_method_info.payer_type
            )
            dd_consumer_id = legacy_payment_method_info.dd_consumer_id
            legacy_dd_stripe_customer_id = (
                legacy_payment_method_info.legacy_dd_stripe_customer_id
            )
        else:
            self.log.error("[create_payment_method] invalid input. must provide id")
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT
            )

        if not pgp_customer_res_id:
            self.log.info(
                "[create_payment_method] can't find pgp_customer_resource_id",
                payer_lookup_id=payer_lookup_id,
                payer_reference_id_type=payer_reference_id_type,
            )
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT
            )

        # step 2: create PGP payment_method
        stripe_payment_method: StripePaymentMethod = await self.payment_method_client.pgp_create_payment_method(
            token=token, country=pgp_country
        )
        self.log.info(
            "[create_payment_method] create stripe payment_method completed",
            payer_lookup_id=payer_lookup_id,
            pgp_payment_method_res_id=stripe_payment_method.id,
            payer_reference_id_type=payer_reference_id_type,
            legacy_dd_stripe_customer_id=legacy_dd_stripe_customer_id,
        )

        # step 3: de-dup same payment_method by card fingerprint
        is_dedup_card_logic_active: bool = runtime.get_bool(
            "payin/feature-flags/enable_dedup_payment_method_card.bool", True
        )
        if is_dedup_card_logic_active:
            try:
                exist_pm: RawPaymentMethod = await self.payment_method_client.get_duplicate_payment_method(
                    stripe_payment_method=stripe_payment_method,
                    payer_reference_id_type=payer_reference_id_type,
                    pgp_customer_resource_id=pgp_customer_res_id,
                    dd_consumer_id=dd_consumer_id,
                    legacy_dd_stripe_customer_id=legacy_dd_stripe_customer_id,
                )
            except PaymentMethodReadError:
                pass
            else:
                self.log.info(
                    "[create_payment_method] duplicate card is found. return the existing one",
                    dd_consumer_id=dd_consumer_id,
                    pgp_payment_method_res_id=stripe_payment_method.id,
                )
                return exist_pm, True
        # step 4: attach PGP payment_method
        attach_stripe_payment_method: StripePaymentMethod = await self.payment_method_client.pgp_attach_payment_method(
            pgp_payment_method_res_id=stripe_payment_method.id,
            pgp_customer_id=pgp_customer_res_id,
            country=pgp_country,
        )
        self.log.info(
            "[create_payment_method] attach stripe payment_method completed",
            payer_lookup_id=payer_lookup_id,
            payer_reference_id_type=payer_reference_id_type,
            pgp_customer_res_id=pgp_customer_res_id,
            pgp_payment_method_res_id=attach_stripe_payment_method.id,
        )

        # step 5: crete pgp_payment_method and stripe_card objects
        payer_id: Optional[UUID] = None
        if raw_payer and raw_payer.payer_entity:
            payer_id = raw_payer.payer_entity.id

        raw_payment_method: RawPaymentMethod = await self.payment_method_client.create_raw_payment_method(
            payment_method_id=generate_object_uuid(),
            pgp_code=pgp_code,
            stripe_payment_method=attach_stripe_payment_method,
            payer_id=payer_id,
            dd_consumer_id=dd_consumer_id,
            legacy_dd_stripe_customer_id=legacy_dd_stripe_customer_id,
            is_scanned=is_scanned,
            is_active=is_active,
        )

        # step 6: set as default payment_method
        if set_default:
            stripe_customer = await self.payer_client.pgp_update_customer_default_payment_method(
                country=pgp_country,
                pgp_customer_resource_id=pgp_customer_res_id,
                pgp_payment_method_resource_id=attach_stripe_payment_method.id,
            )

            self.log.info(
                "[create_payment_method] PGP update default_payment_method completed",
                payer_lookup_id=payer_lookup_id,
                payer_reference_id_type=payer_reference_id_type,
                default_payment_method=stripe_customer.invoice_settings.default_payment_method,
            )

            if raw_payer:
                await self.payer_client.update_default_payment_method(
                    raw_payer=raw_payer,
                    payment_method_ids=PaymentMethodIds(
                        pgp_payment_method_resource_id=raw_payment_method.pgp_payment_method_resource_id,
                        dd_stripe_card_id=raw_payment_method.legacy_dd_stripe_card_id,
                        payment_method_id=raw_payment_method.payment_method_id,
                    ),
                )
        return raw_payment_method, False

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

        # TODO: step 2: if force_update is true, we should retrieve the payment_method from payment providers

        return raw_payment_method.to_payment_method()

    async def list_payment_methods(
        self,
        payer_lookup_id: MixedUuidStrType,
        payer_reference_id_type: PayerReferenceIdType,
        active_only: bool,
        sort_by: PaymentMethodSortKey,
        force_update: bool,
    ) -> PaymentMethodList:
        # Precondition of v1 API is that all the payers has been migrated from maindb_consumers to paymentdb_payers.
        payer_entity: PayerDbEntity = await self.payer_client.get_payer_entity(
            payer_lookup_id=payer_lookup_id,
            payer_reference_id_type=payer_reference_id_type,
        )
        payment_method_list = await self.payment_method_client.get_payment_method_list_by_stripe_customer_id(
            stripe_customer_id=payer_entity.primary_pgp_payer_resource_id,
            country=payer_entity.country,
            active_only=active_only,
            force_update=force_update,
            sort_by=sort_by,
        )
        return PaymentMethodList(
            count=len(payment_method_list), has_more=False, data=payment_method_list
        )

    async def list_payment_methods_legacy(
        self,
        country: CountryCode,
        active_only: bool,
        sort_by: PaymentMethodSortKey,
        force_update: bool,
        dd_consumer_id: str = None,
        stripe_customer_id: str = None,
    ) -> PaymentMethodList:

        payment_method_list: List[PaymentMethod] = []
        if dd_consumer_id:
            payment_method_list = await self.payment_method_client.get_payment_method_list_by_dd_consumer_id(
                dd_consumer_id=dd_consumer_id,
                country=country,
                active_only=active_only,
                force_update=force_update,
                sort_by=sort_by,
            )
        elif stripe_customer_id:
            payment_method_list = await self.payment_method_client.get_payment_method_list_by_stripe_customer_id(
                stripe_customer_id=stripe_customer_id,
                country=country,
                active_only=active_only,
                force_update=force_update,
                sort_by=sort_by,
            )
        else:
            raise PaymentMethodListError(
                error_code=PayinErrorCode.PAYMENT_METHOD_LIST_INVALID_PAYER_TYPE
            )
        return PaymentMethodList(
            count=len(payment_method_list), has_more=False, data=payment_method_list
        )

    async def delete_payment_method(
        self,
        payment_method_id: str,
        payment_method_id_type: Optional[PaymentMethodIdType] = None,
        country: Optional[CountryCode] = CountryCode.US,
    ) -> PaymentMethod:
        """
        Detach a payment method.

        :param payment_method_id: DoorDash payment method id.
        :param payment_method_id_type: type of payment method.
        :param country: country only used for v0 legacy path.
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
                mixed_payer_id=raw_payment_method.payer_id(),
                payer_reference_id_type=PayerReferenceIdType.PAYER_ID,
            )
        elif raw_payment_method.stripe_card_entity:
            try:
                raw_payer = await self.payer_client.get_raw_payer(
                    mixed_payer_id=raw_payment_method.stripe_card_entity.external_stripe_customer_id,
                    payer_reference_id_type=PayerReferenceIdType.STRIPE_CUSTOMER_ID,
                )
            except PayerReadError as e:
                if e.error_code != PayinErrorCode.PAYER_READ_NOT_FOUND:
                    raise
                else:
                    # existing DSJ consumers, continue to detach the payment method.
                    self.log.warn(
                        "[delete_payment_method] can't find payer by stripe_customer_id. could be DSJ existing consumer.",
                        stripe_customer_id=raw_payment_method.stripe_card_entity.external_stripe_customer_id,
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
