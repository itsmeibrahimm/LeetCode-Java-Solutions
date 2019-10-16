import logging
import time

import pytest
from payin_v0_client import ApiException

from tests.payin.helper import PaymentUtil
from tests.payin.v0 import cart_payment_v0_client, payment_method_v0_client

logger = logging.getLogger(__name__)

CART_AMOUNT = 1000


def test_create_legacy_cart_payment_with_no_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=False,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is False


def test_create_legacy_cart_payment_with_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=True,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is True


def test_create_legacy_cart_payment_with_invalid_request():
    error_code = -1
    error_reason = ""
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    create_cart_payment_legacy_request = PaymentUtil.get_create_legacy_cart_payment_request(
        amount=CART_AMOUNT,
        country="US",
        currency="usd",
        dd_consumer_id=1,
        dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
        stripe_card_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        stripe_customer_id=stripe_customer_id,
        reference_id="1",
        reference_id_type="37",
        delay_capture=False,
    )
    try:
        create_cart_payment_legacy_request.legacy_payment = {}
        cart_payment_v0_client.create_cart_payment_with_http_info(
            create_cart_payment_legacy_request=create_cart_payment_legacy_request
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 422
    assert error_reason == "Unprocessable Entity"


@pytest.mark.skip(reason="flaky test")
def test_update_legacy_cart_payment_higher_without_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=False,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is False
    updated_amount = 1200
    updated_cart_payment = cart_payment_v0_client.adjust_cart_payment_with_http_info(
        dd_charge_id=cart_payment[0].dd_charge_id,
        update_cart_payment_legacy_request=PaymentUtil.get_update_cart_payment_legacy_request(
            updated_amount=updated_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_amount + CART_AMOUNT
    assert updated_cart_payment[0].delay_capture is False


def test_update_legacy_cart_payment_lower_without_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=False,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is False
    updated_amount = -200
    updated_cart_payment = cart_payment_v0_client.adjust_cart_payment_with_http_info(
        dd_charge_id=cart_payment[0].dd_charge_id,
        update_cart_payment_legacy_request=PaymentUtil.get_update_cart_payment_legacy_request(
            updated_amount=updated_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_amount + CART_AMOUNT
    assert updated_cart_payment[0].delay_capture is False


def test_update_legacy_cart_payment_lower_with_invalid_amount():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=False,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is False
    updated_amount = -1200
    error_code = -1
    try:
        cart_payment_v0_client.adjust_cart_payment_with_http_info(
            dd_charge_id=cart_payment[0].dd_charge_id,
            update_cart_payment_legacy_request=PaymentUtil.get_update_cart_payment_legacy_request(
                updated_amount=updated_amount
            ),
        )
    except ApiException as e:
        error_code = e.status
    assert error_code == 500


def test_update_legacy_cart_payment_higher_with_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=True,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is True
    updated_amount = 1200
    updated_cart_payment = cart_payment_v0_client.adjust_cart_payment_with_http_info(
        dd_charge_id=cart_payment[0].dd_charge_id,
        update_cart_payment_legacy_request=PaymentUtil.get_update_cart_payment_legacy_request(
            updated_amount=updated_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_amount + CART_AMOUNT
    assert updated_cart_payment[0].delay_capture is True


def test_update_legacy_cart_payment_lower_with_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=True,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is True
    updated_amount = -200
    updated_cart_payment = cart_payment_v0_client.adjust_cart_payment_with_http_info(
        dd_charge_id=cart_payment[0].dd_charge_id,
        update_cart_payment_legacy_request=PaymentUtil.get_update_cart_payment_legacy_request(
            updated_amount=updated_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_amount + CART_AMOUNT
    assert updated_cart_payment[0].delay_capture is True


def test_update_legacy_cart_payment_with_cart_payment_not_found():
    error_code = -1
    error_reason = ""
    try:
        cart_payment_v0_client.adjust_cart_payment_with_http_info(
            dd_charge_id=int(time.time()),
            update_cart_payment_legacy_request=PaymentUtil.get_update_cart_payment_legacy_request(
                updated_amount=100
            ),
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 404
    assert error_reason == "Not Found"


def test_cancel_legacy_cart_payment_without_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=False,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is False
    deleted_cart_payment = cart_payment_v0_client.cancel_cart_payment_with_http_info(
        dd_charge_id=cart_payment[0].dd_charge_id, body={}
    )
    assert deleted_cart_payment[1] == 200


def test_cancel_legacy_cart_payment_with_delay_capture():
    payer = PaymentUtil.create_payer()
    assert payer[1] == 201
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            dd_stripe_customer_id=payer[0].dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    cart_payment = cart_payment_v0_client.create_cart_payment_with_http_info(
        create_cart_payment_legacy_request=PaymentUtil.get_create_legacy_cart_payment_request(
            amount=CART_AMOUNT,
            country="US",
            currency="usd",
            dd_consumer_id=1,
            dd_stripe_card_id=payment_method[0].dd_stripe_card_id,
            stripe_card_id=payment_method[
                0
            ].payment_gateway_provider_details.payment_method_id,
            stripe_customer_id=stripe_customer_id,
            reference_id="1",
            reference_id_type="37",
            delay_capture=True,
        )
    )
    assert cart_payment[1] == 201
    assert cart_payment[0].amount == CART_AMOUNT
    assert cart_payment[0].delay_capture is True
    deleted_cart_payment = cart_payment_v0_client.cancel_cart_payment_with_http_info(
        dd_charge_id=cart_payment[0].dd_charge_id, body={}
    )
    assert deleted_cart_payment[1] == 200


def test_cancel_legacy_cart_payment_with_cart_payment_not_found():
    error_code = -1
    try:
        cart_payment_v0_client.cancel_cart_payment_with_http_info(
            dd_charge_id=int(time.time()), body={}
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
    assert (
        error_code == 500
    )  # Todo: Add cart payment not found error handling for v0 cancel API
