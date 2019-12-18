import asyncio
import csv
from typing import Union
from uuid import UUID

from app.commons.context.app_context import AppContext
from app.commons.context.logger import get_logger
from app.payin.core.cart_payment.processor import CartPaymentProcessor
from app.payin.core.cart_payment.types import IntentStatus
from app.payin.core.exceptions import CartPaymentCreateError, PayinErrorCode
from scripts.payin.helper import get_cart_payment_processor, get_cart_payment_repo

__all__ = ["fail_one_payment_in_state", "fail_payments_in_state"]

log = get_logger("fail_payment")


async def _fail_payment(
    payment_intent_id: Union[str, UUID],
    intent_status: IntentStatus,
    cart_payment_processor: CartPaymentProcessor,
):
    if not isinstance(payment_intent_id, UUID):
        try:
            payment_intent_id = UUID(payment_intent_id)
        except ValueError:
            log.exception(f"malformed payment_intent_id={payment_intent_id}")
            return

    log.info(f"Attempt to fail payment intent id={payment_intent_id}")

    cart_payment_repo = get_cart_payment_repo(
        cart_payment_processor=cart_payment_processor
    )

    payment_intent = await cart_payment_repo.get_payment_intent_by_id(payment_intent_id)
    if not payment_intent:
        log.info(f"Payment intent not found, id={payment_intent.id}")
        return

    # If intent is not in required state, return immediately
    if payment_intent.status != intent_status:
        log.info(
            f"Payment intent not in correct status, id={payment_intent.id}, status={payment_intent.status}, target_status={intent_status}"
        )
        return

    pgp_payment_intent = await cart_payment_processor.cart_payment_interface.get_cart_payment_submission_pgp_intent(
        payment_intent=payment_intent
    )

    _, legacy_stripe_charge = await cart_payment_processor.legacy_payment_interface.find_existing_payment_charge(
        charge_id=payment_intent.legacy_consumer_charge_id,
        idempotency_key=payment_intent.idempotency_key,
    )

    if not legacy_stripe_charge:
        log.info(f"Stripe charge for payment intent not found, id={payment_intent.id}")
        return

    if payment_intent:
        log.info(f"Found payment intent={payment_intent.json()}")
        try:
            creation_exception = CartPaymentCreateError(
                error_code=PayinErrorCode.PAYMENT_INTENT_CREATE_ERROR,
                provider_charge_id=None,
                provider_error_code=None,
                provider_decline_code=None,
                has_provider_error_details=False,
            )
            await cart_payment_processor._update_state_after_provider_error(
                creation_exception=creation_exception,
                payment_intent=payment_intent,
                pgp_payment_intent=pgp_payment_intent,
                legacy_stripe_charge=legacy_stripe_charge,
            )
            log.info(f"payment intent marked as failed, id={payment_intent.id}")
        except Exception:
            log.exception(
                f"payment intent could not be marked as failed, id={payment_intent.id}"
            )


def fail_payments_in_state(
    *, file_path: str, intent_status: IntentStatus, app_context: AppContext
):
    # Bulk update of marking payment intents as failed.  The file at file_path is expected to contain a list of payment intent IDs.
    # Each is then used to mark a payment as failed.
    cart_payment_processor = get_cart_payment_processor(app_context=app_context)
    loop = asyncio.get_event_loop()
    with open(file_path) as data_file:
        # CSV reader is used in case we need to customize intent_status per intent in the future.
        csv_data = csv.reader(data_file)
        for row in csv_data:
            try:
                loop.run_until_complete(
                    _fail_payment(
                        payment_intent_id=row[0],
                        intent_status=intent_status,
                        cart_payment_processor=cart_payment_processor,
                    )
                )
            except:
                log.exception(
                    "Failed to mark intent as failed", payment_intent_id=row[0]
                )


def fail_one_payment_in_state(
    *,
    payment_intent_id: Union[str, UUID],
    intent_status: IntentStatus,
    app_context: AppContext,
):
    """
    Scripts to mark a single payment as failed.  The payment is identified by payment_intent_id, which must be
    in the state identified by intent_status.
    Args:
        payment_intent_id: ID of payment intent.
        intent_status: Expected current state of payment intent.
        app_context: app_context

    Returns: None

    """

    cart_payment_processor = get_cart_payment_processor(app_context=app_context)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(
        _fail_payment(
            payment_intent_id=payment_intent_id,
            intent_status=intent_status,
            cart_payment_processor=cart_payment_processor,
        )
    )
