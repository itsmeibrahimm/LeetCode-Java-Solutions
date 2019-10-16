import logging

import pytest
from payin_v0_client import DefaultPaymentMethodV0, UpdatePayerRequestV0, ApiException

from tests.payin.v0 import payer_v0_client, payment_method_v0_client
from tests.payin.helper import StripeUtil, PaymentUtil

logger = logging.getLogger(__name__)


def test_create_and_get_with_stripe_customer_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    retrieved_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=new_stripe_customer["id"],
        payer_id_type="stripe_customer_id",
        force_update=True,
    )
    assert retrieved_payer[1] == 200


def test_payer_not_found_incorrect_id():
    try:
        payer_v0_client.get_payer_with_http_info(
            payer_id="INCORRECT_ID", payer_id_type="stripe_customer_id"
        )
    except ApiException as e:
        assert e.status == 404


def test_get_payer_with_invalid_id():
    try:
        payer_v0_client.get_payer_with_http_info(
            payer_id="INVALID_ID", payer_id_type="stripe_customer_id", force_update=True
        )
    except ApiException as e:
        assert e.status == 404


@pytest.mark.skip(
    reason="No existing way to update payment method using stripe customer id"
)
def test_update_payer_with_stripe_customer_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    new_payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=new_stripe_customer.id
        )
    )
    assert new_payment_method[1] == 201

    default_payment_method = DefaultPaymentMethodV0(
        dd_stripe_card_id=new_payment_method[0].dd_stripe_card_id
    )
    update_payer_request_v0 = UpdatePayerRequestV0(
        default_payment_method=default_payment_method,
        country="US",
        payer_type="marketplace",
    )
    update_payment_method = payer_v0_client.update_payer_with_http_info(
        payer_id=new_stripe_customer.id,
        payer_id_type="stripe_customer_id",
        update_payer_request_v0=update_payer_request_v0,
    )
    assert update_payment_method[1] == 200
    get_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=new_stripe_customer["id"],
        payer_id_type="stripe_customer_id",
        force_update=True,
    )
    default_payment_method_id = next(
        iter(
            [
                payment_method.default_payment_method_id
                for payment_method in get_payer[0].payment_gateway_provider_customers
                if payment_method.default_payment_method_id is not None
            ]
        ),
        None,
    )
    assert default_payment_method_id is not None
    assert (
        default_payment_method_id == new_payment_method[0].card.payment_provider_card_id
    )


@pytest.mark.skip(
    reason="No existing way to insert stripe_customer_id to the stripe_customer table & get stripe_customer_serial_id"
)
def test_update_payer_with_stripe_customer_serial_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    # TODO: Figure out a way to insert stripe_customer_id to the stripe_customer table & get stripe_customer_serial_id
    stripe_customer_serial_id = StripeUtil.get_stripe_customer_serial_id(
        new_stripe_customer["id"]
    )
    # todo - create a new payment_method with v0 client for legacy fields
    new_payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payer_id": stripe_customer_serial_id,
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert new_payment_method[1] == 201
    update_payment_method = payer_v0_client.update_payer_with_http_info(
        stripe_customer_serial_id, {"default_payment_method": new_payment_method[0]}
    )
    assert update_payment_method[1] == 200
    get_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=stripe_customer_serial_id,
        payer_id_type="stripe_customer_serial_id",
        force_update=True,
    )
    default_payment_method_id = next(
        iter(
            [
                payment_method.default_payment_method_id
                for payment_method in get_payer[0].payment_gateway_provider_customers
                if payment_method.default_payment_method_id is not None
            ]
        ),
        None,
    )
    assert default_payment_method_id is not None
    assert (
        default_payment_method_id == new_payment_method[0].card.payment_provider_card_id
    )
