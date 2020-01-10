import logging
import time

import pytest
from payin_v0_client import ApiException

from tests.payin.helper import PaymentUtil
from tests.payin.v0 import payment_method_v0_client
from tests.payin.v1 import payment_method_v1_client

logger = logging.getLogger(__name__)


def test_create_get_delete_payment_method_with_payment_method_id():
    # step 1: create a payment method using stripe_customer_id
    payer = PaymentUtil.create_payer()
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            legacy_dd_stripe_customer_id=payer[0].legacy_dd_stripe_customer_id,
        )
    )
    logger.info(payment_method[0])
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None
    logger.info(payment_method[0])

    # step 2: get payment method using payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id_type="payment_method_id",
        payment_method_id=payment_method[0].id,
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment method using stripe_customer_id and payment_method_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].id,
        payment_method_id_type="payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id,
        payment_method_id_type="payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


def test_create_get_delete_payment_method_with_stripe_payment_method_id():
    # step 1: create a payment method using stripe_customer_id
    payer = PaymentUtil.create_payer()
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            legacy_dd_stripe_customer_id=payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using stripe_customer_id and stripe_payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_id and stripe_payment_method_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify that payment_method has been deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


def test_create_get_delete_payment_method_with_dd_stripe_card_id():
    # step 1: create StripeCard and attach to StripeCustomer
    payer = PaymentUtil.create_payer()
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            legacy_dd_stripe_customer_id=payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment_method using stripe_customer_id and stripe_card_serial_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].dd_stripe_card_id,
        payment_method_id_type="dd_stripe_card_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_id and stripe_card_serial_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].dd_stripe_card_id,
        payment_method_id_type="dd_stripe_card_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    retrieved_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].dd_stripe_card_id,
        payment_method_id_type="dd_stripe_card_id",
    )
    assert retrieved_payment_method[1] == 200
    assert retrieved_payment_method[0].id == payment_method[0].id
    assert retrieved_payment_method[0] == delete_payment_method[0]
    assert retrieved_payment_method[0].deleted_at is not None


def test_create_payment_method_with_invalid_input():
    try:
        payment_method_v0_client.create_payment_method_with_http_info(
            create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
                stripe_customer_id=["INVALID"],
                legacy_dd_stripe_customer_id=int(time.time()),
            )
        )
    except ApiException as e:
        assert e.status == 422


def test_get_payment_method_with_invalid_input():
    payer = PaymentUtil.create_payer()
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            legacy_dd_stripe_customer_id=payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    try:
        payment_method_v0_client.get_payment_method_with_http_info(
            payment_method_id=payment_method[0].id,
            payment_method_id_type="dd_stripe_card_id",
        )
    except ApiException as e:
        assert e.status == 500


def test_get_payment_method_with_missing_input():
    with pytest.raises(TypeError):
        payment_method_v0_client.get_payment_method_with_http_info(
            payment_method_id_type="dd_stripe_card_id"
        )


def test_create_v0_get_v1_payment_method():
    payer = PaymentUtil.create_payer()
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            legacy_dd_stripe_customer_id=payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    retrieved_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert retrieved_payment_method[1] == 200
    assert retrieved_payment_method[0].id == payment_method[0].id


def test_create_v0_delete_v1_payment_method():
    payer = PaymentUtil.create_payer()
    stripe_customer_id = (
        payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    payment_method = payment_method_v0_client.create_payment_method_with_http_info(
        create_payment_method_request_v0=PaymentUtil.get_payment_method_v0_info(
            stripe_customer_id=stripe_customer_id,
            legacy_dd_stripe_customer_id=payer[0].legacy_dd_stripe_customer_id,
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    delete_payment_method = payment_method_v1_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    retrieved_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id,
        payment_method_id_type="payment_method_id",
    )
    assert retrieved_payment_method[0].id == delete_payment_method[0].id
    assert retrieved_payment_method[0].deleted_at is not None
