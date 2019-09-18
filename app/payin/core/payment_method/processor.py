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
from app.payin.core.exceptions import PaymentMethodCreateError, PayinErrorCode
from app.payin.core.payer.model import RawPayer
from app.payin.core.payment_method.model import (
    PaymentMethod,
    RawPaymentMethod,
    PaymentMethodList,
)
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.payment_method.types import SortKey
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
        payer_id: UUID = None,
        dd_consumer_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        country: Optional[CountryCode] = CountryCode.US,
    ) -> PaymentMethod:
        """
        Implementation to create a payment method.

        :param pgp_code:
        :param token:
        :param payer_id:
        :param dd_consumer_id:
        :param stripe_customer_id:
        :param country:
        :return:
        """

        # step 1: lookup pgp_customer_resource_id and country information
        # TODO: retrieve pgp_resouce_id from pgp_customers table, instead of payers.legacy_stripe_customer_id
        if not (payer_id or dd_consumer_id or stripe_customer_id):
            self.log.info(f"[create_payment_method] invalid input. must provide id")
            raise PaymentMethodCreateError(
                error_code=PayinErrorCode.PAYMENT_METHOD_CREATE_INVALID_INPUT,
                retryable=False,
            )

        pgp_customer_res_id: Optional[str]
        pgp_country: Optional[str] = country
        raw_payer: RawPayer
        if payer_id:
            raw_payer = await self.payer_client.get_raw_payer(
                payer_id, PayerIdType.PAYER_ID
            )
            pgp_customer_res_id = raw_payer.pgp_customer_id()
            pgp_country = raw_payer.country()
        else:  # v0 path with legacy information
            if stripe_customer_id:
                pgp_customer_res_id = stripe_customer_id
            else:
                raw_payer = await self.payer_client.get_raw_payer(
                    dd_consumer_id, PayerIdType.DD_CONSUMER_ID
                )
                pgp_customer_res_id = raw_payer.pgp_customer_id()

        # TODO: perform Payer's lazy creation

        # step 2: create and attach PGP payment_method
        stripe_payment_method: StripePaymentMethod = await self.payment_method_client.pgp_create_and_attach_payment_method(
            token=token,
            pgp_customer_id=pgp_customer_res_id,
            country=pgp_country,
            attached=True,
        )

        self.log.info(
            "[create_payment_method] create stripe payment_method completed and attached to customer",
            payer_id=payer_id,
            pgp_customer_res_id=pgp_customer_res_id,
            pgp_payment_method_res_id=stripe_payment_method.id,
        )

        # step 3: crete pgp_payment_method and stripe_card objects
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.create_raw_payment_method(
            id=generate_object_uuid(),
            pgp_code=pgp_code,
            stripe_payment_method=stripe_payment_method,
            payer_id=payer_id,
            legacy_consumer_id=dd_consumer_id,
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
        Implementation of get payment method

        :param payer_id:
        :param payment_method_id:
        :param payer_id_type:
        :param payment_method_id_type:
        :param country:
        :param force_update:
        :return: PaymentMethod object.
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
        Implementation of delete/detach a payment method.

        :param payment_method_id:
        :param payment_method_id_type:
        :param country:
        :return: PaymentMethod object
        """

        # step 1: find payment_method.
        raw_payment_method: RawPaymentMethod = await self.payment_method_client.get_raw_payment_method_without_payer_auth(
            payment_method_id=payment_method_id,
            payment_method_id_type=payment_method_id_type,
        )
        pgp_payment_method_id: str = raw_payment_method.pgp_payment_method_id()

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
