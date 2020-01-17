from typing import Optional

from doordash_python_stats.ddstats import doorstats_global
from fastapi import Depends
from privacy import common_pb2, action_pb2
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext
from app.commons.context.req_context import get_logger_from_req
from app.commons.providers.stripe.stripe_models import Customer as StripeCustomer
from app.commons.runtime import runtime
from app.commons.timing import track_func
from app.commons.types import CountryCode, PgpCode
from app.commons.utils.legacy_utils import payer_id_type_to_payer_reference_id_type
from app.payin.core.cart_payment.processor import (
    LegacyPaymentInterface,
    CartPaymentInterface,
)
from app.payin.core.payer.model import (
    Payer,
    RawPayer,
    PaymentGatewayProviderCustomer,
    DeletePayerSummary,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import (
    LegacyPayerInfo,
    DeletePayerRequestStatus,
    DeletePayerRedactingText,
)
from app.payin.core.payment_method.model import RawPaymentMethod, PaymentMethodIds
from app.payin.core.payment_method.payment_method_client import PaymentMethodClient
from app.payin.core.types import PayerIdType, PaymentMethodIdType
from app.payin.kafka.delete_payer_message_processor import send_response
from app.payin.repository.payer_repo import DeletePayerRequestDbEntity
from app.payin.core.exceptions import (
    PayerReadError,
    PayinErrorCode,
    PayerDeleteError,
    PaymentMethodUpdateError,
    CartPaymentUpdateError,
    LegacyStripeChargeUpdateError,
)


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
                mixed_payer_id=legacy_payer_info.payer_id,
                payer_reference_id_type=payer_id_type_to_payer_reference_id_type(
                    payer_id_type=legacy_payer_info.payer_id_type
                ),
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
                mixed_payer_id=legacy_payer_info.payer_id,
                payer_reference_id_type=payer_id_type_to_payer_reference_id_type(
                    payer_id_type=legacy_payer_info.payer_id_type
                ),
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
            payment_method_ids=PaymentMethodIds(
                pgp_payment_method_resource_id=raw_pm.pgp_payment_method_resource_id,
                dd_stripe_card_id=raw_pm.legacy_dd_stripe_card_id,
                payment_method_id=raw_pm.payment_method_id,
            ),
        )

        return updated_raw_payer.to_payer()


@tracing.track_breadcrumb(processor_name="delete_payer_processor", only_trackable=True)
class DeletePayerProcessor:
    def __init__(
        self,
        max_retries: int,
        log: BoundLogger = Depends(get_logger_from_req),
        app_context: AppContext = Depends(AppContext),
        payer_client: PayerClient = Depends(PayerClient),
        payment_method_client: PaymentMethodClient = Depends(PaymentMethodClient),
        cart_payment_interface: CartPaymentInterface = Depends(CartPaymentInterface),
        legacy_payment_interface: LegacyPaymentInterface = Depends(
            LegacyPaymentInterface
        ),
    ):
        self.cart_payment_interface = cart_payment_interface
        self.payer_client = payer_client
        self.payment_method_client = payment_method_client
        self.max_retries = max_retries
        self.log = log
        self.app_context = app_context
        self.legacy_payment_interface = legacy_payment_interface

    @track_func
    @tracing.trackable
    async def delete_payer(self, delete_payer_request: DeletePayerRequestDbEntity):
        """

        :param delete_payer_request:
        :return:
        Steps:
            1. Try to individually update or delete pii from each table or domain
            2. If all of above individual update/delete successful send success response and mark status as successful
            3. If any of above individual update/delete unsuccessful increment retry_count, and if max retry count
            reached mark status as failure and send failure response
            4. Update the request db entry, with new status, retry_count, summary and acknowledged fields.
        """
        self.log.info(
            "[delete_payer] Commencing delete payer.",
            consumer_id=delete_payer_request.consumer_id,
            client_request_id=delete_payer_request.client_request_id,
        )

        consumer_id = delete_payer_request.consumer_id
        delete_payer_summary = DeletePayerSummary.parse_raw(
            delete_payer_request.summary
        )
        acknowledged = delete_payer_request.acknowledged
        status = delete_payer_request.status
        retry_count = delete_payer_request.retry_count

        stripe_cards_status = await self.remove_pii_from_stripe_cards(
            consumer_id, delete_payer_summary
        )
        stripe_charges_status = await self.remove_pii_from_stripe_charges(
            consumer_id, delete_payer_summary
        )
        cart_payments_status = await self.remove_pii_from_cart_payments(
            consumer_id, delete_payer_summary
        )
        stripe_customer_status = await self.delete_stripe_customer(
            consumer_id, delete_payer_summary
        )

        self.update_delete_payer_summary(
            delete_payer_summary,
            stripe_cards_status,
            stripe_charges_status,
            cart_payments_status,
            stripe_customer_status,
        )

        pii_removal_successful = self.is_pii_removal_successfull(
            stripe_cards_status,
            stripe_charges_status,
            cart_payments_status,
            stripe_customer_status,
        )

        if pii_removal_successful:
            self.log.info(
                "[delete_payer] Delete payer successful.",
                consumer_id=delete_payer_request.consumer_id,
                client_request_id=delete_payer_request.client_request_id,
            )
            doorstats_global.incr("delete-payer.success")
            status = DeletePayerRequestStatus.SUCCEEDED
            acknowledged = await send_response(
                app_context=self.app_context,
                log=self.log,
                request_id=str(delete_payer_request.client_request_id),
                action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
                status=common_pb2.StatusCode.COMPLETE,
                response=delete_payer_summary.json(),
            )
        else:
            self.log.info(
                "[delete_payer] Delete payer unsuccessful.",
                consumer_id=delete_payer_request.consumer_id,
                client_request_id=delete_payer_request.client_request_id,
            )
            doorstats_global.incr("delete-payer.error")
            retry_count += 1
            if retry_count >= self.max_retries:
                self.log.error(
                    "[delete_payer] Maximum number of retry attempts reached. "
                    "Please have someone from support take a look at the issue.",
                    consumer_id=delete_payer_request.consumer_id,
                    client_request_id=delete_payer_request.client_request_id,
                )
                # TODO Paging logic here, JIRA created - https: // doordash.atlassian.net / browse / PP - 124
                doorstats_global.incr("delete-payer.failure")
                status = DeletePayerRequestStatus.FAILED
                self.update_delete_payer_summary_after_max_retries(delete_payer_summary)
                acknowledged = await send_response(
                    app_context=self.app_context,
                    log=self.log,
                    request_id=str(delete_payer_request.client_request_id),
                    action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
                    status=common_pb2.StatusCode.ERROR,
                    response=delete_payer_summary.json(),
                )

        try:
            await self.payer_client.update_delete_payer_request(
                delete_payer_request.client_request_id,
                status,
                delete_payer_summary.json(),
                retry_count,
                acknowledged,
            )
        except PayerDeleteError:
            self.log.exception(
                "[delete_payer] Database exception occurred with updating delete payer request",
                consumer_id=delete_payer_request.consumer_id,
                client_request_id=delete_payer_request.client_request_id,
            )
            doorstats_global.incr("delete-payer.exception")
            raise

    async def remove_pii_from_stripe_cards(
        self, consumer_id: int, delete_payer_summary: DeletePayerSummary
    ) -> bool:
        if (
            delete_payer_summary.doordash_domain_redact.stripe_cards.status
            == DeletePayerRequestStatus.SUCCEEDED
        ):
            return True

        try:
            updated_stripe_cards = await self.payment_method_client.update_stripe_cards_remove_pii(
                consumer_id
            )
            for stripe_card in updated_stripe_cards:
                if (
                    stripe_card.last4 != DeletePayerRedactingText.XXXX
                    or stripe_card.dynamic_last4 != DeletePayerRedactingText.XXXX
                ):
                    self.log.error(
                        "[remove_pii_from_stripe_cards] Pii removal from stripe cards unsuccessful",
                        consumer_id=consumer_id,
                    )
                    return False
            self.log.info(
                "[remove_pii_from_stripe_cards] Pii removed from stripe cards",
                consumer_id=consumer_id,
            )
            return True
        except PaymentMethodUpdateError:
            self.log.exception(
                "[remove_pii_from_stripe_cards] Database exception occurred with removing pii from stripe cards",
                consumer_id=consumer_id,
            )
            return False

    async def remove_pii_from_stripe_charges(
        self, consumer_id: int, delete_payer_summary: DeletePayerSummary
    ) -> bool:
        if (
            delete_payer_summary.doordash_domain_redact.stripe_charges.status
            == DeletePayerRequestStatus.SUCCEEDED
        ):
            return True

        failed_updates = False
        """Get all consumer charges associated with consumer"""
        legacy_consumer_charge_ids = await self.legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id(
            consumer_id
        )
        for legacy_consumer_charge_id in legacy_consumer_charge_ids:
            """Get all stripe charges associated with individual consumer charge"""
            legacy_stripe_charges = await self.legacy_payment_interface.get_legacy_stripe_charges_by_charge_id(
                legacy_consumer_charge_id
            )
            for legacy_stripe_charge in legacy_stripe_charges:
                """If stripe charge has not been successfully updated previously update it now"""
                if (
                    legacy_stripe_charge.description
                    != DeletePayerRedactingText.REDACTED
                ):
                    try:
                        updated_legacy_stripe_charge = await self.legacy_payment_interface.update_legacy_stripe_charge_remove_pii(
                            legacy_stripe_charge.id
                        )
                        if (
                            updated_legacy_stripe_charge
                            and updated_legacy_stripe_charge.description
                            != DeletePayerRedactingText.REDACTED
                        ):
                            failed_updates = True
                    except LegacyStripeChargeUpdateError:
                        failed_updates = True
                        self.log.exception(
                            "[remove_pii_from_stripe_charges] Database exception occurred while removing pii from stripe charge",
                            consumer_id=consumer_id,
                            legacy_consumer_charge_id=legacy_consumer_charge_id,
                            legacy_stripe_charge_id=legacy_stripe_charge.id,
                        )
        """If no of the updates failed then updated the status to succeeded"""
        if not failed_updates:
            self.log.info(
                "[remove_pii_from_stripe_charges] Pii removed from stripe charges",
                consumer_id=consumer_id,
            )
        else:
            self.log.error(
                "[remove_pii_from_stripe_charges] Pii removal from stripe charges unsuccessful",
                consumer_id=consumer_id,
            )
        return not failed_updates

    async def remove_pii_from_cart_payments(
        self, consumer_id: int, delete_payer_summary: DeletePayerSummary
    ) -> bool:
        if (
            delete_payer_summary.doordash_domain_redact.cart_payments.status
            == DeletePayerRequestStatus.SUCCEEDED
        ):
            return True

        try:
            updated_cart_payments = await self.cart_payment_interface.update_cart_payments_remove_pii(
                consumer_id
            )
            for cart_payment in updated_cart_payments:
                if cart_payment.client_description != DeletePayerRedactingText.REDACTED:
                    self.log.error(
                        "[remove_pii_from_cart_payments] Pii removal from cart_payments unsuccessful",
                        consumer_id=consumer_id,
                    )
                    return False
            self.log.info(
                "[remove_pii_from_cart_payments] Pii removed from cart_payments",
                consumer_id=consumer_id,
            )
            return True
        except CartPaymentUpdateError:
            self.log.exception(
                "[remove_pii_from_cart_payments] Database exception occurred with removing pii from cart_payments",
                consumer_id=consumer_id,
            )
            return False

    async def delete_stripe_customer(
        self, consumer_id: int, delete_payer_summary: DeletePayerSummary
    ) -> bool:
        if (
            delete_payer_summary.stripe_domain_redact.customer.status
            == DeletePayerRequestStatus.SUCCEEDED
        ):
            return True

        stripe_cards = await self.payment_method_client.get_stripe_cards_for_consumer_id(
            consumer_id
        )

        """
            Since a consumer can be associated with multiple cards, each of which can
            have external_stripe_customer_id present or absent. Hence we loop through
            each card to find at least one external_stripe_customer_id which should
            ideally be unique
        """
        stripe_customer_id = None
        for stripe_card in stripe_cards:
            if stripe_card.external_stripe_customer_id:
                stripe_customer_id = stripe_card.external_stripe_customer_id
                break

        if not stripe_customer_id:
            self.log.info(
                "[delete_stripe_customer] No stripe customer id found for consumer",
                consumer_id=consumer_id,
            )
            return True

        """
            Since we don't have access to consumer table we don't know stripe country
            for consumer, which we need to determine api key to use.
        """
        for country_code in CountryCode:
            self.log.info(
                "[delete_stripe_customer] Trying to delete stripe customer for country",
                consumer_id=consumer_id,
                stripe_customer_id=stripe_customer_id,
                country_code=country_code,
            )
            try:
                stripe_response = await self.payer_client.delete_pgp_customer(
                    country_code, stripe_customer_id
                )
                if stripe_response and stripe_response.deleted:
                    """Here we return early if stripe customer delete was successful in any of the pods"""
                    self.log.info(
                        "[delete_stripe_customer] Customer successfully deleted from stripe",
                        consumer_id=consumer_id,
                    )
                    return True
            except PayerDeleteError:
                self.log.exception(
                    "[delete_stripe_customer] Exception occurred while deleting customer from stripe",
                    consumer_id=consumer_id,
                )
        return False

    def is_pii_removal_successfull(
        self,
        stripe_cards_status: bool,
        stripe_charges_status: bool,
        cart_payments_status: bool,
        stripe_customer_status: bool,
    ) -> bool:
        return (
            stripe_cards_status
            and stripe_charges_status
            and cart_payments_status
            and stripe_customer_status
        )

    def update_delete_payer_summary(
        self,
        delete_payer_summary: DeletePayerSummary,
        stripe_cards_status: bool,
        stripe_charges_status: bool,
        cart_payments_status: bool,
        stripe_customer_status: bool,
    ):
        if stripe_cards_status:
            delete_payer_summary.doordash_domain_redact.stripe_cards.status = (
                DeletePayerRequestStatus.SUCCEEDED
            )
        if stripe_charges_status:
            delete_payer_summary.doordash_domain_redact.stripe_charges.status = (
                DeletePayerRequestStatus.SUCCEEDED
            )
        if cart_payments_status:
            delete_payer_summary.doordash_domain_redact.cart_payments.status = (
                DeletePayerRequestStatus.SUCCEEDED
            )
        if stripe_customer_status:
            delete_payer_summary.stripe_domain_redact.customer.status = (
                DeletePayerRequestStatus.SUCCEEDED
            )

    def update_delete_payer_summary_after_max_retries(
        self, delete_payer_summary: DeletePayerSummary
    ):
        """

        :param delete_payer_summary:
        :return:
        Update summary with failed status for operations that are still in progress
        """
        if (
            delete_payer_summary.doordash_domain_redact.stripe_cards.status
            == DeletePayerRequestStatus.IN_PROGRESS
        ):
            delete_payer_summary.doordash_domain_redact.stripe_cards.status = (
                DeletePayerRequestStatus.FAILED
            )
        if (
            delete_payer_summary.doordash_domain_redact.stripe_charges.status
            == DeletePayerRequestStatus.IN_PROGRESS
        ):
            delete_payer_summary.doordash_domain_redact.stripe_charges.status = (
                DeletePayerRequestStatus.FAILED
            )
        if (
            delete_payer_summary.doordash_domain_redact.cart_payments.status
            == DeletePayerRequestStatus.IN_PROGRESS
        ):
            delete_payer_summary.doordash_domain_redact.cart_payments.status = (
                DeletePayerRequestStatus.FAILED
            )
        if (
            delete_payer_summary.stripe_domain_redact.customer.status
            == DeletePayerRequestStatus.IN_PROGRESS
        ):
            delete_payer_summary.stripe_domain_redact.customer.status = (
                DeletePayerRequestStatus.FAILED
            )
