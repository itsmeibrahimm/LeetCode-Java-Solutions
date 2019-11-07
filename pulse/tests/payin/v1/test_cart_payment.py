import logging
import uuid
from datetime import datetime

from payin_v1_client import ApiException

from tests.payin.helper import PaymentUtil
from tests.payin.v1 import cart_payment_v1_client, payment_method_v1_client

logger = logging.getLogger(__name__)

CART_AMOUNT = 1000


def test_create_cart_payment_without_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=False,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].amount == CART_AMOUNT
    assert new_cart_payment[0].delay_capture is False


def test_create_cart_payment_with_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=True,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].amount == CART_AMOUNT
    assert new_cart_payment[0].delay_capture is True


def test_create_cart_payment_with_incorrect_payment_method():
    payer_1 = PaymentUtil.create_payer(dd_payer_id=2)[0]
    payer_2 = PaymentUtil.create_payer(dd_payer_id=3)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=payer_2.id
        )
    )
    error_code = -1
    error_reason = ""
    try:
        cart_payment_v1_client.create_cart_payment_with_http_info(
            create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
                payer=payer_1,
                payment_method=new_payment_method,
                country="US",
                currency="usd",
                reference_id="1",
                reference_id_type="37",
                amount=CART_AMOUNT,
                delay_capture=False,
            )
        )
    except ApiException as e:
        error_code = e.status
        error_reason = e.reason
    assert error_code == 403
    assert error_reason == "Forbidden"


def test_create_cart_payment_with_invalid_payment_method():
    temp_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payer = PaymentUtil.create_payer()[0]
    temp_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=temp_payer.id
        )
    )
    temp_payment_method.id = "INVALID_ID"
    error_code = -1
    error_reason = ""
    try:
        cart_payment_v1_client.create_cart_payment_with_http_info(
            create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
                payer=new_payer,
                payment_method=temp_payment_method,
                country="US",
                currency="usd",
                reference_id="1",
                reference_id_type="37",
                amount=CART_AMOUNT,
                delay_capture=False,
            )
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 422
    assert error_reason == "Unprocessable Entity"


def test_update_cart_payment_higher_without_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=False,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is False
    assert new_cart_payment[0].amount == CART_AMOUNT
    updated_cart_amount = 1200
    updated_cart_payment = cart_payment_v1_client.adjust_cart_payment_with_http_info(
        cart_payment_id=new_cart_payment[0].id,
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_request(
            payer=new_payer, updated_amount=updated_cart_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_cart_amount
    assert updated_cart_payment[0].deleted_at is None


def test_update_cart_payment_lower_without_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=False,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is False
    updated_cart_amount = 800
    updated_cart_payment = cart_payment_v1_client.adjust_cart_payment_with_http_info(
        cart_payment_id=new_cart_payment[0].id,
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_request(
            payer=new_payer, updated_amount=updated_cart_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_cart_amount
    assert updated_cart_payment[0].deleted_at is None


def test_update_cart_payment_higher_with_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=True,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is True
    updated_cart_amount = 1200
    updated_cart_payment = cart_payment_v1_client.adjust_cart_payment_with_http_info(
        cart_payment_id=new_cart_payment[0].id,
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_request(
            payer=new_payer, updated_amount=updated_cart_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_cart_amount
    assert updated_cart_payment[0].deleted_at is None


def test_update_cart_payment_lower_with_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=True,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is True
    updated_cart_amount = 800
    updated_cart_payment = cart_payment_v1_client.adjust_cart_payment_with_http_info(
        cart_payment_id=new_cart_payment[0].id,
        update_cart_payment_request=PaymentUtil.get_update_cart_payment_request(
            payer=new_payer, updated_amount=updated_cart_amount
        ),
    )
    assert updated_cart_payment[1] == 200
    assert updated_cart_payment[0].amount == updated_cart_amount
    assert updated_cart_payment[0].deleted_at is None


def test_update_cart_payment_cart_payment_not_found():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    updated_cart_amount = 800
    error_code = -1
    error_reason = ""
    try:
        cart_payment_v1_client.adjust_cart_payment_with_http_info(
            cart_payment_id=str(uuid.uuid4()),
            update_cart_payment_request=PaymentUtil.get_update_cart_payment_request(
                payer=new_payer, updated_amount=updated_cart_amount
            ),
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 404
    assert error_reason == "Not Found"


def test_update_cart_payment_cart_payment_with_invalid_amount():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=True,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is True
    updated_cart_amount = -100
    error_code = -1
    error_reason = ""
    try:
        cart_payment_v1_client.adjust_cart_payment_with_http_info(
            cart_payment_id=new_cart_payment[0].id,
            update_cart_payment_request=PaymentUtil.get_update_cart_payment_request(
                payer=new_payer, updated_amount=updated_cart_amount
            ),
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 422
    assert error_reason == "Unprocessable Entity"


def test_cancel_cart_payment_with_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=True,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is True
    deleted_cart_payment = cart_payment_v1_client.cancel_cart_payment_with_http_info(
        cart_payment_id=new_cart_payment[0].id, body={}
    )
    assert deleted_cart_payment[1] == 200
    assert deleted_cart_payment[0].deleted_at is not None
    assert isinstance(deleted_cart_payment[0].deleted_at, datetime)
    assert deleted_cart_payment[0].deleted_at == deleted_cart_payment[0].updated_at


def test_cancel_cart_payment_without_delay_capture():
    new_payer = PaymentUtil.create_payer(dd_payer_id=2)[0]
    new_payment_method = payment_method_v1_client.create_payment_method(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            new_payer.id
        )
    )
    new_cart_payment = cart_payment_v1_client.create_cart_payment_with_http_info(
        create_cart_payment_request=PaymentUtil.get_create_cart_payment_request(
            payer=new_payer,
            payment_method=new_payment_method,
            country="US",
            currency="usd",
            reference_id="1",
            reference_id_type="37",
            amount=CART_AMOUNT,
            delay_capture=False,
        )
    )
    assert new_cart_payment[1] == 201
    assert new_cart_payment[0].delay_capture is False
    deleted_cart_payment = cart_payment_v1_client.cancel_cart_payment_with_http_info(
        cart_payment_id=new_cart_payment[0].id, body={}
    )
    assert deleted_cart_payment[1] == 200
    assert deleted_cart_payment[0].deleted_at is not None
    assert isinstance(deleted_cart_payment[0].deleted_at, datetime)
    assert deleted_cart_payment[0].deleted_at == deleted_cart_payment[0].updated_at


def test_cancel_cart_payment_with_cart_payment_not_found():
    error_code = -1
    error_reason = ""
    try:
        cart_payment_v1_client.cancel_cart_payment_with_http_info(
            cart_payment_id=str(uuid.uuid4()), body={}
        )
    except ApiException as e:
        logger.log(msg=str(e), level=logging.INFO)
        error_code = e.status
        error_reason = e.reason
    assert error_code == 404
    assert error_reason == "Not Found"
