from abc import ABC, abstractmethod
from typing import Dict

from fastapi import Depends
from structlog import BoundLogger

from app.commons.context.req_context import get_logger_from_req
from app.payin.api.webhook.v1.request import StripeWebHookEvent
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
        self.log.info(f"Handling {self.TYPE_NAME} webhook for country {country_code}")


class WebhookHandlerContainer:
    """
    Webhooks are a little nasty so we use a container to work around FastAPI DI limitations. Not a good pattern
    to use for other cases since it loads far more dependencies than it actually needs.
    """

    def __init__(
        self,
        log: BoundLogger = Depends(get_logger_from_req),
        charge_refund_handler: ChargeRefundHandler = Depends(ChargeRefundHandler),
    ):
        self.log = log
        self.internal_container: Dict[str, BaseWebhookHandler] = {}

        # Add handlers for new webhooks here !
        self._add_new_handler(ChargeRefundHandler.TYPE_NAME, charge_refund_handler)

    def _add_new_handler(self, type: str, handler: BaseWebhookHandler):
        self.internal_container = self.internal_container or {}
        self.internal_container[type] = handler

    def provide_handler(self, type: str) -> BaseWebhookHandler:
        try:
            return self.internal_container[type]
        except KeyError:
            raise UnknownTypeException(
                f"WebhookHandlerContainer does not have a valid handler for requests type {type}"
            )


class WebhookProcessor:
    def __init__(
        self,
        stripe_webhook_event: StripeWebHookEvent,
        container: WebhookHandlerContainer = Depends(WebhookHandlerContainer),
    ):
        self.event = stripe_webhook_event
        self.container = container

    async def process_webhook(self, country_code: str):
        handler = self.container.provide_handler(self.event.type)
        await handler(self.event, country_code)
