import logging
import random
import uuid

from payin_v1_client import ApiException

from tests.payin.helper import PaymentUtil, StripeUtil
from tests.payin.v0 import payer_v0_client
from tests.payin.v1 import payer_v1_client, payment_method_v1_client

logger = logging.getLogger(__name__)


def test_create_and_get_payer():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)
    stripe_customer_id = (
        new_payer[0].payment_gateway_provider_customers[0].payment_provider_customer_id
    )
    stripe_customer = StripeUtil.get_stripe_customer(
        stripe_customer_id=stripe_customer_id
    )
    assert stripe_customer
    assert stripe_customer.id == stripe_customer_id
    assert stripe_customer.description == new_payer[0].description
    retrieved_payer = payer_v1_client.get_payer_with_http_info(payer_id=new_payer[0].id)
    assert retrieved_payer[1] == 200
    assert retrieved_payer[0] == new_payer[0]


def test_create_and_get_payer_with_non_numeric_id():
    error_code_non_numeric_id = -1
    error_message_non_numeric_id = ""
    try:
        payer_v1_client.create_payer_with_http_info(
            create_payer_request=PaymentUtil.get_create_payer_request(
                payer_reference_id="abc",
                country="US",
                payer_reference_id_type="dd_drive_store_id",
            )
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code_non_numeric_id = e.status
        error_message_non_numeric_id = e.reason
    assert error_code_non_numeric_id == 400
    assert error_message_non_numeric_id == "Bad Request"


def test_create_two_payers_with_same_id():
    payer_reference_id = str(random.randint(1, 2147483647))
    new_payer_one = payer_v1_client.create_payer_with_http_info(
        create_payer_request=PaymentUtil.get_create_payer_request(
            payer_reference_id=payer_reference_id,
            country="US",
            payer_reference_id_type="dd_drive_store_id",
        )
    )
    assert new_payer_one[1] in (200, 201)
    stripe_customer_id = (
        new_payer_one[0]
        .payment_gateway_provider_customers[0]
        .payment_provider_customer_id
    )
    stripe_customer = StripeUtil.get_stripe_customer(
        stripe_customer_id=stripe_customer_id
    )
    assert stripe_customer
    assert stripe_customer.id == stripe_customer_id
    assert stripe_customer.description == new_payer_one[0].description
    new_payer_two = payer_v1_client.create_payer_with_http_info(
        create_payer_request=PaymentUtil.get_create_payer_request(
            payer_reference_id=payer_reference_id,
            country="US",
            payer_reference_id_type="dd_drive_store_id",
        )
    )
    assert new_payer_two[1] == 200


def test_get_payer_with_wrong_input():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)

    # Testing for wrong data type (Expected String)
    error_code_invalid_data_type = -1
    error_message_invalid_date_type = ""
    try:
        payer_v1_client.get_payer_with_http_info(payer_id=1)
    except ApiException as e:
        error_code_invalid_data_type = e.status
        error_message_invalid_date_type = e.reason
    assert error_code_invalid_data_type == 422
    assert error_message_invalid_date_type == "Unprocessable Entity"

    # Testing for incorrect id
    error_code_incorrect_id = -1
    error_message_incorrect_id = ""
    try:
        payer_v1_client.get_payer_with_http_info(payer_id=str(uuid.uuid4()))
    except ApiException as e:
        error_code_incorrect_id = e.status
        error_message_incorrect_id = e.reason
    assert error_code_incorrect_id == 404
    assert error_message_incorrect_id == "Not Found"


def test_update_payer_with_payer_id():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)
    new_payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer[0].id, set_default=True
        )
    )
    assert new_payment_method[1] in (200, 201)
    update_payment_method = payer_v1_client.update_payer_default_payment_method_by_id_with_http_info(
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
        default_payment_method_id
        == new_payment_method[0].payment_gateway_provider_details.payment_method_id
    )


def test_create_v1_get_v0_payer_by_payer_id():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)

    get_payer = payer_v0_client.get_payer_with_http_info(
        payer_id_type="payer_id", payer_id=new_payer[0].id
    )
    assert get_payer[1] == 200
    logger.info(new_payer[0])


def test_create_v1_get_v0_payer_by_stripe_customer_serial_id():
    new_payer = PaymentUtil.create_payer()
    assert new_payer[1] in (200, 201)

    get_payer = payer_v0_client.get_payer_with_http_info(
        payer_id_type="dd_stripe_customer_serial_id",
        payer_id=new_payer[0].legacy_dd_stripe_customer_id,
    )
    assert get_payer[1] == 200
    logger.info(new_payer[0])
