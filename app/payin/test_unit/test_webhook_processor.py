import uuid
from unittest.mock import MagicMock, patch

import pytest
from asynctest import mock

from app.commons.types import PgpCode, Currency
from app.payin.core.cart_payment.model import PaymentIntent
from app.payin.core.cart_payment.types import IntentStatus, LegacyConsumerChargeId
from app.payin.core.webhook.model import StripeWebHookEvent
from app.payin.core.webhook.processor import PaymentIntentCreatedHandler


class TestPaymentIntentCreatedHandler:
    payment_intent = PaymentIntent(
        id=uuid.uuid4(),
        cart_payment_id=uuid.uuid4(),
        idempotency_key=str(uuid.uuid4()),
        amount_initiated=1000,
        pgp_code=PgpCode.STRIPE,
        resource_id="VALID_RESOURCE_ID",
        status=IntentStatus.PENDING,
        invoice_resource_id="VALID_INVOICE_RESOURCE_ID",
        charge_resource_id="VALID_CHARGE_RESOURCE_ID",
        payment_method_resource_id="VALID_PAYMENT_METHOD_RESOURCE_ID",
        customer_resource_id="VALID_CUSTOMER_RESOURCE_ID",
        currency=Currency.USD,
        amount=1000,
        amount_capturable=0,
        amount_received=0,
        application_fee_amount=0,
        payout_account_id="VALID_PAYOUT_ACCOUNT_ID",
        capture_method="manual",
        country="US",
        legacy_consumer_charge_id=LegacyConsumerChargeId(1),
        created_at=1326853478,
        updated_at=1326853480,
        captured_at=None,
        cancelled_at=None,
    )

    event = StripeWebHookEvent(
        id="evt_00000000000000",
        object="event",
        api_version="2019-05-16",
        created=1326853478,
        data={
            "object": {
                "id": "tr_00000000000000",
                "metadata": {"payment_intent_id": payment_intent.id},
                "status": "pending",
                "amount": 1000,
                "application_fee_amount": 0,
            }
        },
        livemode=True,
        pending_webhooks=1,
        type="payment_intent.created",
    )

    @pytest.fixture()
    def payment_intent_created_handle(self):
        return PaymentIntentCreatedHandler(
            cart_payment_repository=MagicMock(), log=MagicMock()
        )

    @patch(
        "app.payin.repository.cart_payment_repo.CartPaymentRepository.get_payment_intent_by_id",
        return_value=payment_intent,
    )
    async def test_successful_verification_payment_intent(
        self, payment_intent_created_handle
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            assert self.event.data.object["metadata"]["payment_intent_id"] is not None
            return_value = await payment_intent_created_handle.__call__(
                event=self.event, country_code="US"
            )
            assert return_value is True

    @patch(
        "app.payin.repository.cart_payment_repo.CartPaymentRepository.get_payment_intent_by_id",
        return_value=None,
    )
    async def test_unsuccessful_verification_payment_intent_not_found(
        self, payment_intent_created_handle
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            assert self.event.data.object["metadata"]["payment_intent_id"] is not None
            return_value = await payment_intent_created_handle.__call__(
                event=self.event, country_code="US"
            )
            assert return_value is False

    @patch(
        "app.payin.repository.cart_payment_repo.CartPaymentRepository.get_payment_intent_by_id",
        return_value=payment_intent,
    )
    async def test_unsuccessful_verification_payment_intent_no_stripe_id(
        self, payment_intent_created_handle
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            assert self.event.data.object["metadata"]["payment_intent_id"] is not None
            copy_event = self.event
            copy_event.data.id = None
            assert copy_event.data.id is None
            return_value = await payment_intent_created_handle.__call__(
                event=copy_event, country_code="US"
            )
            assert return_value is False

    @patch(
        "app.payin.repository.cart_payment_repo.CartPaymentRepository.get_payment_intent_by_id",
        return_value=payment_intent,
    )
    async def test_unsuccessful_verification_payment_intent_no_payment_intent_id(
        self, payment_intent_created_handle
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            assert self.event.data.object["metadata"]["payment_intent_id"] is not None
            copy_event = self.event
            copy_event.data.object["metadata"]["payment_intent_id"] = None
            assert copy_event.data.object["metadata"]["payment_intent_id"] is None
            return_value = await payment_intent_created_handle.__call__(
                event=copy_event, country_code="US"
            )
            assert return_value is False

    @patch(
        "app.payin.repository.cart_payment_repo.CartPaymentRepository.get_payment_intent_by_id",
        return_value=payment_intent,
    )
    async def test_unsuccessful_verification_payment_intent_mismatch(
        self, payment_intent_created_handle
    ):
        with mock.patch(
            "app.payin.core.feature_flags.stripe_payment_intent_webhook_event_enabled",
            return_value=True,
        ):
            assert self.event.data.object["metadata"]["payment_intent_id"] is not None
            copy_event = self.event
            copy_event.data.object["amount"] = 1200
            assert copy_event.data.object["amount"] != self.event.data.object["amount"]
            return_value = await payment_intent_created_handle.__call__(
                event=copy_event, country_code="US"
            )
            assert return_value is False
