import logging

import pytest
from payin_v0_client import (
    ApiException,
)  # use the ApiException of same version client whose ApiClient has been used

from .utils import StripeUtil, PaymentUtil
from . import payer_v0_client, payer_v1_client, payment_method_v1_client

logger = logging.getLogger(__name__)


def test_create_and_get_payer():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] == 201
    retrieved_payer = payer_v1_client.get_payer_with_http_info(payer_id=new_payer[0].id)
    assert retrieved_payer[1] == 200
    assert retrieved_payer[0] == new_payer[0]


def test_create_and_get_payer_with_non_numeric_id():
    error_code_non_numeric_id = -1
    error_message_non_numeric_id = ""
    try:
        payer_v1_client.create_payer_with_http_info(
            create_payer_request=PaymentUtil.get_payer_info(
                dd_payer_id="abc", payer_type="store"
            )
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code_non_numeric_id = e.status
        error_message_non_numeric_id = e.reason
    assert error_code_non_numeric_id == 422
    assert error_message_non_numeric_id == "Unprocessable Entity"


@pytest.mark.skip(
    reason="Retrieving payer using stripe customer id not implemented yet"
)
def test_create_and_get_with_stripe_customer_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    retrieved_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=new_stripe_customer["id"],
        payer_id_type="stripe_customer_id",
        force_update=True,
    )
    assert retrieved_payer[1] == 200


@pytest.mark.skip(
    reason="No existing way to insert stripe_customer_id to the stripe_customer table & get stripe_customer_serial_id"
)
def test_create_and_get_with_stripe_customer_serial_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    # TODO: Figure out a way to insert stripe_customer_id to the stripe_customer table & get stripe_customer_serial_id
    stripe_customer_serial_id = StripeUtil.get_stripe_customer_serial_id(
        new_stripe_customer["id"]
    )
    retrieved_payer = payer_v0_client.get_payer_with_http_info(
        payer_id=stripe_customer_serial_id,
        payer_id_type="stripe_customer_serial_id",
        force_update=True,
    )
    assert retrieved_payer[1] == 200


def test_create_two_payers_with_same_id():
    new_payer_one = payer_v1_client.create_payer_with_http_info(
        create_payer_request=PaymentUtil.get_payer_info(dd_payer_id=123)
    )
    assert new_payer_one[1] == 201

    new_payer_two = payer_v1_client.create_payer_with_http_info(
        create_payer_request=PaymentUtil.get_payer_info(dd_payer_id=123)
    )
    # FIXME: A new payer should not get created using the same dd_payer_id. Should raise an exception
    assert new_payer_two[1] == 201


def test_create_payer_with_wrong_input():
    payer_info = PaymentUtil.get_payer_info()
    del payer_info["payer_type"]

    error_code = -1
    error_msg = ""

    try:
        payer_v1_client.create_payer_with_http_info(create_payer_request=payer_info)
    except ApiException as e:
        error_code = e.status
        error_msg = e.reason

    assert error_code == 422
    assert error_msg == "Unprocessable Entity"


@pytest.mark.skip(reason="Need to enforce validation at api/presentation layer")
def test_get_payer_with_wrong_input():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] == 201

    # Testing for wrong data type (Expected String)
    error_code_invalid_data_type = -1
    error_message_invalid_date_type = ""
    try:
        payer_v1_client.get_payer_with_http_info(payer_id=1)
    except ApiException as e:
        error_code_invalid_data_type = e.status
        error_message_invalid_date_type = e.reason
    # FIXME: Should throw invalid data type error. Currently throwing 404
    assert error_code_invalid_data_type == 404
    assert error_message_invalid_date_type == "Not Found"

    # Testing for incorrect id
    error_code_incorrect_id = -1
    error_message_incorrect_id = ""
    try:
        payer_v1_client.get_payer_with_http_info(payer_id="abc123")
    except ApiException as e:
        error_code_incorrect_id = e.status
        error_message_incorrect_id = e.reason
    assert error_code_incorrect_id == 404
    assert error_message_incorrect_id == "Not Found"


@pytest.mark.skip(reason="API contract change. need to bump client lib version")
def test_update_payer_with_payer_id():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] == 201
    new_payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request=PaymentUtil.get_payment_method_info(new_payer[0])
    )
    assert new_payment_method[1] == 201
    update_payment_method = payer_v1_client.update_payer_with_http_info(
        new_payer[0].id, {"default_payment_method": new_payment_method[0]}
    )
    assert update_payment_method[1] == 200
    get_payer = payer_v1_client.get_payer_with_http_info(payer_id=new_payer[0].id)
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
    reason="Retrieving payer using stripe customer id not implemented yet"
)
def test_update_payer_with_stripe_customer_id():
    new_stripe_customer = StripeUtil.create_stripe_customer()
    # todo - create a new payment_method with v0 client for legacy fields
    new_payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payer_id": new_stripe_customer["id"],
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert new_payment_method[1] == 201
    update_payment_method = payer_v1_client.update_payer_with_http_info(
        new_stripe_customer["id"], {"default_payment_method": new_payment_method[0]}
    )
    assert update_payment_method[1] == 200
    get_payer = payer_v1_client.get_payer_with_http_info(
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
    new_payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payer_id": stripe_customer_serial_id,
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert new_payment_method[1] == 201
    update_payment_method = payer_v1_client.update_payer_with_http_info(
        stripe_customer_serial_id, {"default_payment_method": new_payment_method[0]}
    )
    assert update_payment_method[1] == 200
    get_payer = payer_v1_client.get_payer_with_http_info(
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
