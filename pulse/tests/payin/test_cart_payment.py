import logging

import pytest
from payin_client import ApiException

from tests.payin import payin_client_pulse
from tests.payin.utils import PaymentUtil

logger = logging.getLogger(__name__)

CART_AMOUNT = 1000
new_payer = PaymentUtil.create_payer()[0]
new_payment_method = payin_client_pulse.create_payment_method_api_v1_payment_methods_post(
    create_payment_method_request=PaymentUtil.get_payment_method_info(new_payer)
)


def test_create_cart_payment():
    new_cart_payment = payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
        create_cart_payment_request=PaymentUtil.get_cart_payment_info(
            new_payer, new_payment_method, CART_AMOUNT
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0]["amount"] == CART_AMOUNT


def test_create_cart_payment_with_incorrect_payment_method():
    temp_payer = PaymentUtil.create_payer()[0]
    error_code = -1
    error_reason = ""
    try:
        payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
            create_cart_payment_request=PaymentUtil.get_cart_payment_info(
                temp_payer, new_payment_method, CART_AMOUNT
            )
        )
    except ApiException as e:
        error_code = e.status
        error_reason = e.reason
    assert error_code == 403
    assert error_reason == "Forbidden"


def test_create_cart_payment_with_invalid_payment_method():
    temp_payer = PaymentUtil.create_payer()[0]
    temp_payment_method = payin_client_pulse.create_payment_method_api_v1_payment_methods_post(
        create_payment_method_request=PaymentUtil.get_payment_method_info(temp_payer)
    )
    temp_payment_method["id"] = "INVALID_ID"
    error_code = -1
    error_reason = ""
    try:
        payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
            create_cart_payment_request=PaymentUtil.get_cart_payment_info(
                new_payer, temp_payment_method, CART_AMOUNT
            )
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 400
    assert error_reason == "Bad Request"


def test_update_cart_payment_higher_manual_capture():
    new_cart_payment = payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
        create_cart_payment_request=PaymentUtil.get_cart_payment_info(
            new_payer, new_payment_method, amount=CART_AMOUNT, capture_method="manual"
        )
    )
    updated_cart_amount = 1200
    updated_cart_payment = payin_client_pulse.update_cart_payment_api_v1_cart_payments_cart_payment_id_adjust_post_with_http_info(
        cart_payment_id=new_cart_payment[0]["id"],
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_info(
            new_payer, updated_cart_amount
        ),
    )
    # Todo: Retrieve cart payment using GET request to verify the updated amount
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0]["amount"] == updated_cart_amount


def test_update_cart_payment_lower_manual_capture():
    new_cart_payment = payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
        create_cart_payment_request=PaymentUtil.get_cart_payment_info(
            new_payer, new_payment_method, amount=CART_AMOUNT, capture_method="manual"
        )
    )
    assert new_cart_payment[1] == 201
    updated_cart_amount = 800
    updated_cart_payment = payin_client_pulse.update_cart_payment_api_v1_cart_payments_cart_payment_id_adjust_post_with_http_info(
        cart_payment_id=new_cart_payment[0]["id"],
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_info(
            new_payer, updated_cart_amount
        ),
    )
    # Todo: Retrieve cart payment using GET request to verify the updated amount
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0]["amount"] == updated_cart_amount


@pytest.mark.skip(reason="Not implemented yet")
def test_update_cart_payment_higher_auto_capture():
    new_cart_payment = payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
        create_cart_payment_request=PaymentUtil.get_cart_payment_info(
            new_payer, new_payment_method, amount=CART_AMOUNT
        )
    )
    assert new_cart_payment[1] == 201
    updated_cart_amount = 1200
    updated_cart_payment = payin_client_pulse.update_cart_payment_api_v1_cart_payments_cart_payment_id_adjust_post_with_http_info(
        cart_payment_id=new_cart_payment[0]["id"],
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_info(
            new_payer, updated_cart_amount
        ),
    )
    # Todo: Retrieve cart payment using GET request to verify the updated amount
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0]["amount"] == updated_cart_amount


@pytest.mark.skip(reason="Not implemented yet")
def test_update_cart_payment_lower_auto_capture():
    new_cart_payment = payin_client_pulse.create_cart_payment_api_v1_cart_payments_post_with_http_info(
        create_cart_payment_request=PaymentUtil.get_cart_payment_info(
            new_payer, new_payment_method, amount=CART_AMOUNT
        )
    )
    assert new_cart_payment[1] == 201
    updated_cart_amount = 800
    updated_cart_payment = payin_client_pulse.update_cart_payment_api_v1_cart_payments_cart_payment_id_adjust_post_with_http_info(
        cart_payment_id=new_cart_payment[0]["id"],
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_info(
            new_payer, updated_cart_amount
        ),
    )
    # Todo: Retrieve cart payment using GET request to verify the updated amount
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0]["amount"] == updated_cart_amount
