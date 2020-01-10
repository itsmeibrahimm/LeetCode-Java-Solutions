import logging

from payin_v0_client import DefaultPaymentMethodV0, UpdatePayerRequestV0, ApiException

from tests.payin.helper import StripeUtil, PaymentUtil
from tests.payin.v0 import payer_v0_client, payment_method_v0_client

logger = logging.getLogger(__name__)


def test_create_and_get_with_stripe_customer_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    retrieved_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=new_stripe_customer["id"],
        payer_id_type="stripe_customer_id",
        force_update=True,
    )
    assert retrieved_payer[1] == 200
    assert (
        retrieved_payer[0]
        .payment_gateway_provider_customers[0]
        .payment_provider_customer_id
        == new_stripe_customer.id
    )


def test_payer_not_found_incorrect_id():
    error_status = -1
    error_reason = ""
    try:
        payer_v0_client.get_payer_with_http_info(
            payer_id="INCORRECT_ID", payer_id_type="stripe_customer_id"
        )
    except ApiException as e:
        error_status = e.status
        error_reason = e.reason
    assert error_status == 404
    assert error_reason == "Not Found"


def test_get_payer_with_invalid_id():
    error_status = -1
    error_reason = ""
    try:
        payer_v0_client.get_payer_with_http_info(
            payer_id="INVALID_ID", payer_id_type="stripe_customer_id", force_update=True
        )
    except ApiException as e:
        error_status = e.status
        error_reason = e.reason
    assert error_status == 404
    assert error_reason == "Not Found"


def test_update_payer_with_stripe_customer_id():
    # step 1: Create a payment method
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)
    new_payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=new_payer[0]
            .payment_gateway_provider_customers[0]
            .payment_provider_customer_id,
            legacy_dd_stripe_customer_id=new_payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert (
        new_payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
        == new_payment_method[0].payment_gateway_provider_details.customer_id
    )
    assert new_payment_method[1] == 201

    # step 2: Update payment method for the payer
    default_payment_method = DefaultPaymentMethodV0(
        dd_stripe_card_id=new_payment_method[0].dd_stripe_card_id
    )
    update_payer_request_v0 = UpdatePayerRequestV0(
        default_payment_method=default_payment_method, country="US", payer_type="store"
    )
    updated_payer = payer_v0_client.update_payer_with_http_info(
        payer_id=new_payer[0]
        .payment_gateway_provider_customers[0]
        .payment_provider_customer_id,
        payer_id_type="stripe_customer_id",
        update_payer_request_v0=update_payer_request_v0,
    )
    assert updated_payer[1] == 200

    # step 3: Get the updated payer
    get_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=new_payer[0]
        .payment_gateway_provider_customers[0]
        .payment_provider_customer_id,
        payer_id_type="stripe_customer_id",
    )
    assert get_payer[1] == 200

    # step 4: Verify default payment method for the payer
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
        default_payment_method_id
        == new_payment_method[0].payment_gateway_provider_details.payment_method_id
    )


def test_update_payer_with_stripe_customer_serial_id():
    # step 1: Create a payment method
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)
    new_payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=new_payer[0]
            .payment_gateway_provider_customers[0]
            .payment_provider_customer_id,
            legacy_dd_stripe_customer_id=new_payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert (
        new_payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
        == new_payment_method[0].payment_gateway_provider_details.customer_id
    )
    assert new_payment_method[1] == 201

    # step 2: Update payment method for the payer
    default_payment_method = DefaultPaymentMethodV0(
        dd_stripe_card_id=new_payment_method[0].dd_stripe_card_id
    )
    update_payer_request_v0 = UpdatePayerRequestV0(
        default_payment_method=default_payment_method, country="US", payer_type="store"
    )
    updated_payer = payer_v0_client.update_payer_with_http_info(
        payer_id=new_payer[0].legacy_dd_stripe_customer_id,
        payer_id_type="dd_stripe_customer_serial_id",
        update_payer_request_v0=update_payer_request_v0,
    )
    assert updated_payer[1] == 200

    # step 3: Get the updated payer
    get_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=new_payer[0].legacy_dd_stripe_customer_id,
        payer_id_type="dd_stripe_customer_serial_id",
    )
    assert get_payer[1] == 200
    assert get_payer[0].id == new_payer[0].id

    # step 4: Verify default payment method for the payer
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
        default_payment_method_id
        == new_payment_method[0].payment_gateway_provider_details.payment_method_id
    )
