from abc import ABC, abstractmethod
from typing import Dict, cast, Optional
from uuid import UUID

from fastapi import Depends
from structlog.stdlib import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.payin.core import feature_flags
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.core.webhook.model import StripeWebHookEvent
from app.payin.repository.cart_payment_repo import CartPaymentRepository


class UnknownTypeException(Exception):
    """
    Indicates an object/handler was requested from our Webhook DI container that does not exist
    """

    pass


class WebhookHandlerError(Exception):
    """
    Generic Error indicating that the webhook handler encountered an unrecoveralbe error
    """

    pass


class BaseWebhookHandler(ABC):
    @abstractmethod
    async def __call__(self, event: StripeWebHookEvent, country_code: str):
        ...


class ChargeRefundHandler(BaseWebhookHandler):
    TYPE_NAME = "charge.refund"

    def __init__(
        self,
        cart_payment_repository: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.log = log
        self.cart_payment_repository = cart_payment_repository

    async def __call__(self, event: StripeWebHookEvent, country_code: str):
        self.log.info(
            "Handling webhook", event_type=self.TYPE_NAME, country=country_code
        )


class PaymentIntentAmountCapturableUpdatedHandler(BaseWebhookHandler):
    TYPE_NAME = "payment_intent.amount_capturable_updated"

    def __init__(
        self,
        cart_payment_repository: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.log = log
        self.cart_payment_repository = cart_payment_repository

    async def __call__(self, event: StripeWebHookEvent, country_code: str):
        self.log.info(
            "Handling webhook", event_type=self.TYPE_NAME, country=country_code
        )


class PaymentIntentCreatedHandler(BaseWebhookHandler):
    TYPE_NAME = "payment_intent.created"

    def __init__(
        self,
        cart_payment_repository: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.log = log
        self.cart_payment_repository = cart_payment_repository

    def _verify_payment_intent_blob(
        self, payment_intent: PaymentIntent, payment_intent_blob
    ):
        return (
            payment_intent.status == payment_intent_blob.get("status", None)
            and payment_intent.amount == payment_intent_blob.get("amount", None)
            and payment_intent.application_fee_amount
            == payment_intent_blob.get("application_fee_amount", None)
        )

    async def __call__(self, event: StripeWebHookEvent, country_code: str):
        self.log.info(
            "Handling webhook", event_type=self.TYPE_NAME, country=country_code
        )
        if not feature_flags.stripe_payment_intent_webhook_event_enabled():
            self.log.info("handle_stripe_payment_intent_webhook turned off.")
            return False
        webhook_data = event.data.object
        stripe_id = webhook_data.get("id", None)
        if not stripe_id:
            self.log.info("not valid stripe_id.")
            return False
        payment_intent_id: UUID = webhook_data.get("metadata", {}).get(
            "payment_intent_id", None
        )
        if not payment_intent_id:
            self.log.info("payment_intent_id not found in metadata. Unable to verify")
            return False
        payment_intent = await self.cart_payment_repository.get_payment_intent_by_id_from_primary(
            id=payment_intent_id
        )
        if not payment_intent:
            self.log.error(
                "Payment intent record not found for the incoming Stripe webhook: ",
                webhook_data=str(webhook_data),
            )
            return False
        if not self._verify_payment_intent_blob(payment_intent, webhook_data):
            self.log.error(
                "Data mismatch for payment intent record for incoming Stripe webhook: ",
                webhook_data=str(webhook_data),
            )
            return False
        self.log.info(
            "Finished handling webhook", event_type=self.TYPE_NAME, country=country_code
        )
        return True


class PaymentIntentPaymentFailedHandler(BaseWebhookHandler):
    TYPE_NAME = "payment_intent.payment_failed"

    def _verify_payment_intent_blob(
        self, payment_intent: PaymentIntent, payment_intent_blob
    ):
        return (
            payment_intent.status == payment_intent_blob.get("status", None)
            and payment_intent.status == "cancelled"
            and payment_intent.amount == payment_intent_blob.get("amount", None)
            and payment_intent.application_fee_amount
            == payment_intent_blob.get("application_fee_amount", None)
        )

    def __init__(
        self,
        cart_payment_repository: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.log = log
        self.cart_payment_repository = cart_payment_repository

    async def __call__(self, event: StripeWebHookEvent, country_code: str):
        self.log.info(
            "Handling webhook", event_type=self.TYPE_NAME, country=country_code
        )
        if not feature_flags.stripe_payment_intent_webhook_event_enabled():
            self.log.info("handle_stripe_payment_intent_webhook turned off.")
            return False
        webhook_data = event.data.object
        stripe_id = webhook_data.get("id", None)
        if not stripe_id:
            self.log.info("not valid stripe_id.")
            return False
        payment_intent_id: UUID = webhook_data.get("metadata", {}).get(
            "payment_intent_id", None
        )
        if not payment_intent_id:
            self.log.info("payment_intent_id not found in metadata. Unable to verify")
            return False
        payment_intent = await self.cart_payment_repository.get_payment_intent_by_id_from_primary(
            id=payment_intent_id
        )
        if not payment_intent:
            self.log.error(
                "Payment intent record not found for the incoming Stripe webhook: ",
                webhook_data=str(webhook_data),
            )
            return False
        if not self._verify_payment_intent_blob(payment_intent, webhook_data):
            self.log.error(
                "Data mismatch for payment intent record for incoming Stripe webhook: ",
                webhook_data=str(webhook_data),
            )
            return False
        self.log.info(
            "Finished handling webhook", event_type=self.TYPE_NAME, country=country_code
        )
        return True


class PaymentIntentSucceededHandler(BaseWebhookHandler):
    TYPE_NAME = "payment_intent.succeeded"

    def _verify_payment_intent_blob(
        self, payment_intent: PaymentIntent, payment_intent_blob
    ):
        return (
            payment_intent.captured_at is not None
            and payment_intent.status == IntentStatus.SUCCEEDED
            and payment_intent.amount == payment_intent_blob["amount_received"]
        )

    def __init__(
        self,
        cart_payment_repository: CartPaymentRepository = Depends(
            CartPaymentRepository.get_repository
        ),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.log = log
        self.cart_payment_repository = cart_payment_repository

    async def __call__(self, event: StripeWebHookEvent, country_code: str):
        self.log.info(
            "Handling webhook", event_type=self.TYPE_NAME, country=country_code
        )
        if not feature_flags.stripe_payment_intent_webhook_event_enabled():
            self.log.info("handle_stripe_payment_intent_webhook turned off.")
            return False
        webhook_data = event.data.object
        stripe_id = webhook_data.get("id", None)
        if not stripe_id:
            self.log.info("not valid stripe_id.")
            return False
        payment_intent_id: UUID = webhook_data.get("metadata", {}).get(
            "payment_intent_id", None
        )
        if not payment_intent_id:
            self.log.info("payment_intent_id not found in metadata. Unable to verify")
            return False
        payment_intent = await self.cart_payment_repository.get_payment_intent_by_id_from_primary(
            id=payment_intent_id
        )
        if not payment_intent:
            self.log.error(
                "Payment intent record not found for the incoming Stripe webhook: ",
                webhook_data=str(webhook_data),
            )
            return False
        if not self._verify_payment_intent_blob(payment_intent, webhook_data):
            self.log.error(
                "Data mismatch for payment intent record for incoming Stripe webhook: ",
                webhook_data=str(webhook_data),
                captured_at=payment_intent.captured_at,
                status=payment_intent.status,
                amount=payment_intent.amount,
            )
            return False
        self.log.info(
            "Finished handling webhook", event_type=self.TYPE_NAME, country=country_code
        )
        return True


class WebhookHandlerContainer:
    """
    Webhooks are a little nasty so we use a container to work around FastAPI DI limitations. Not a good pattern
    to use for other cases since it loads far more dependencies than it actually needs.
    """

    def __init__(
        self,
        log: BoundLogger = Depends(get_logger_from_req),
        charge_refund_handler: ChargeRefundHandler = Depends(ChargeRefundHandler),
        payment_intent_amount_capturable_update_handler: PaymentIntentAmountCapturableUpdatedHandler = Depends(
            PaymentIntentAmountCapturableUpdatedHandler
        ),
        payment_intent_created_handler: PaymentIntentCreatedHandler = Depends(
            PaymentIntentCreatedHandler
        ),
        payment_intent_failed_handler: PaymentIntentPaymentFailedHandler = Depends(
            PaymentIntentPaymentFailedHandler
        ),
        payment_intent_succeeded_handler: PaymentIntentSucceededHandler = Depends(
            PaymentIntentSucceededHandler
        ),
    ):
        self.log = log
        self.internal_container: Dict[str, BaseWebhookHandler] = {}

        # Add handlers for new webhooks here !
        self._add_new_handler(ChargeRefundHandler.TYPE_NAME, charge_refund_handler)
        self._add_new_handler(
            PaymentIntentAmountCapturableUpdatedHandler.TYPE_NAME,
            payment_intent_amount_capturable_update_handler,
        )
        self._add_new_handler(
            PaymentIntentCreatedHandler.TYPE_NAME, payment_intent_created_handler
        )
        self._add_new_handler(
            PaymentIntentPaymentFailedHandler.TYPE_NAME, payment_intent_failed_handler
        )
        self._add_new_handler(
            PaymentIntentSucceededHandler.TYPE_NAME, payment_intent_succeeded_handler
        )

    def _add_new_handler(self, type: str, handler: BaseWebhookHandler):
        self.internal_container = self.internal_container or {}
        self.internal_container[type] = handler

    def provide_handler(self, type: str) -> Optional[BaseWebhookHandler]:
        try:
            return self.internal_container[type]
        except KeyError:
            self.log.info(
                f"WebhookHandlerContainer does not have a valid handler for requests type {type}"
            )
            return None


class WebhookProcessor:
    def __init__(
        self, container: WebhookHandlerContainer = Depends(WebhookHandlerContainer)
    ):
        self.container = container

    async def process_webhook(
        self, country_code: str, stripe_webhook_event: StripeWebHookEvent
    ):
        handler = self.container.provide_handler(stripe_webhook_event.type)
        if handler:
            await handler(cast(StripeWebHookEvent, stripe_webhook_event), country_code)
