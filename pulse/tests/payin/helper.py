import random
import uuid

import stripe
from payin_v0_client import (
    CreatePaymentMethodRequestV0,
    CreateCartPaymentLegacyRequest,
    LegacyPaymentInfo,
    CorrelationIds,
    UpdateCartPaymentLegacyRequest,
)
from payin_v1_client import (
    CreatePayerRequest,
    CreatePaymentMethodRequestV1,
    CreateCartPaymentRequestV1,
    AppPayinCoreCartPaymentModelSplitPayment,
    AppPayinCoreCartPaymentModelCorrelationIds,
    UpdateCartPaymentRequestV1,
    Payer,
    PayerCorrelationIds,
    PaymentMethod,
)

from tests.config import STRIPE_US_SECRET_KEY
from tests.payin.v1 import payer_v1_client, payment_method_v1_client

additional_payment_info = {
    "metadata": {"is_first_order": "False"},
    "destination": "acct_1FKYqjDpmxeDAkcx",
    "application_fee": 100,
}

split_payment = AppPayinCoreCartPaymentModelSplitPayment(
    payout_account_id=additional_payment_info["destination"],
    application_fee_amount=additional_payment_info["application_fee"],
)


class StripeUtil:
    @staticmethod
    def create_stripe_customer():
        stripe.api_key = STRIPE_US_SECRET_KEY
        return stripe.Customer.create(description="Customer for test.case@example.com")


def get_correlation_ids(reference_id: str, reference_id_type: str):
    return AppPayinCoreCartPaymentModelCorrelationIds(
        reference_id=reference_id, reference_type=reference_id_type
    )


class PaymentUtil:
    @staticmethod
    def get_payment_method_v1_request(payer_id: uuid.UUID, set_default: bool = False):
        return CreatePaymentMethodRequestV1(
            payer_id=payer_id,
            payment_gateway="stripe",
            token="tok_visa",
            is_scanned=True,
            is_active=True,
            set_default=set_default,
        )

    @staticmethod
    def get_payment_method_v0_info(
        stripe_customer_id, legacy_dd_stripe_customer_id: int, set_default: bool = False
    ):
        return CreatePaymentMethodRequestV0(
            stripe_customer_id=stripe_customer_id,
            token="tok_visa",
            is_scanned=True,
            is_active=True,
            set_default=set_default,
            country="US",
            dd_consumer_id=None,
            payer_type="store",
            legacy_dd_stripe_customer_id=legacy_dd_stripe_customer_id,
        )

    @staticmethod
    def get_create_payer_request(
        payer_reference_id: int, country: str, payer_reference_id_type: str
    ):
        payer_reference_ids: PayerCorrelationIds = PayerCorrelationIds(
            payer_reference_id=payer_reference_id,
            payer_reference_id_type=payer_reference_id_type,
        )
        return CreatePayerRequest(
            payer_correlation_ids=payer_reference_ids,
            email=str(payer_reference_id)
            + "-"
            + payer_reference_id_type
            + "@email.com",
            country=country,
            description="test payer creation",
        )

    @staticmethod
    def create_payer(payer_reference_id=random.randint(1, 2147483647)):
        return payer_v1_client.create_payer_with_http_info(
            create_payer_request=PaymentUtil.get_create_payer_request(
                payer_reference_id=payer_reference_id,
                country="US",
                payer_reference_id_type="dd_drive_store_id",
            )
        )

    @staticmethod
    def create_payment_method(payer_id: str, payer_id_type: str):
        if payer_id_type == "dd_payer_id":
            return payment_method_v1_client.create_payment_method(
                create_payment_method_request={
                    "payer_id": payer_id,
                    "payment_gateway": "stripe",
                    "token": "tok_visa",
                }
            )
        elif payer_id_type == "stripe_customer_id":
            return payment_method_v1_client.create_payment_method(
                create_payment_method_request={
                    "payment_gateway": "stripe",
                    "token": "tok_visa",
                    "legacy_payment_info": {"stripe_customer_id": payer_id},
                }
            )

    @staticmethod
    def get_create_cart_payment_request(
        payer: Payer,
        payment_method: PaymentMethod,
        amount: int,
        country: str,
        currency: str,
        reference_id: str,
        reference_id_type: str,
        delay_capture: bool,
        client_description: str = None,
    ):
        return CreateCartPaymentRequestV1(
            amount=amount,
            payment_country=country,
            currency=currency,
            delay_capture=delay_capture,
            idempotency_key=str(uuid.uuid4()),
            client_description="Test_Transaction"
            if not client_description
            else client_description,
            payer_statement_description="Test_Transaction",
            split_payment=split_payment,
            payer_id=payer.id,
            payment_method_id=payment_method.id,
            correlation_ids=get_correlation_ids(
                reference_id=reference_id, reference_id_type=reference_id_type
            ),
            metadata=additional_payment_info["metadata"],
        )

    @staticmethod
    def get_update_cart_payment_request(payer: Payer, updated_amount: int):
        return UpdateCartPaymentRequestV1(
            idempotency_key=str(uuid.uuid4()),
            amount=updated_amount,
            client_description="Test Update Transaction",
        )

    @staticmethod
    def get_create_legacy_cart_payment_request(
        amount: int,
        country: str,
        currency: str,
        dd_consumer_id: int,
        dd_stripe_card_id: int,
        stripe_customer_id: str,
        stripe_card_id: str,
        reference_id: str,
        reference_id_type: str,
        delay_capture: bool,
        client_description: str = None,
    ):
        legacy_payment = LegacyPaymentInfo(
            dd_consumer_id=dd_consumer_id,
            dd_stripe_card_id=dd_stripe_card_id,
            dd_country_id=1,
            stripe_customer_id=stripe_customer_id,
            stripe_card_id=stripe_card_id,
            dd_additional_payment_info=additional_payment_info,
        )
        legacy_correlation_ids = CorrelationIds(
            reference_id=reference_id, reference_type=reference_id_type
        )
        return CreateCartPaymentLegacyRequest(
            amount=amount,
            payment_country=country,
            currency=currency,
            delay_capture=delay_capture,
            idempotency_key=str(uuid.uuid4()),
            client_description="Test Legacy Transaction"
            if not client_description
            else client_description,
            payer_statement_description="Test Transaction",
            split_payment=split_payment,
            legacy_payment=legacy_payment,
            legacy_correlation_ids=legacy_correlation_ids,
            payer_country=country,
        )

    @staticmethod
    def get_update_cart_payment_legacy_request(updated_amount: int):
        return UpdateCartPaymentLegacyRequest(
            idempotency_key=str(uuid.uuid4()),
            amount=updated_amount,
            client_description="Update Transaction",
            split_payment=split_payment,
            dd_additional_payment_info=additional_payment_info,
        )
