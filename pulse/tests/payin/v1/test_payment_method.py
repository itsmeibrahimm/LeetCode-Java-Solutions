import logging
import uuid

import pytest
from payin_v1_client import ApiException

from tests.payin.helper import PaymentUtil
from tests.payin.v0 import payment_method_v0_client
from tests.payin.v1 import payment_method_v1_client

logger = logging.getLogger(__name__)


def test_create_payment_method_with_invalid_input():
    try:
        payment_method_v1_client.create_payment_method_with_http_info(
            create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
                payer_id=123
            )
        )
    except ApiException as e:
        assert e.status == 422


def test_create_payment_method_with_payer_not_found():
    try:
        payment_method_v1_client.create_payment_method_with_http_info(
            create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
                payer_id=str(uuid.uuid4())
            )
        )
    except ApiException as e:
        assert e.status == 404


def test_successful_get_payment_method():
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=test_payer.id
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    retrieved_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert retrieved_payment_method[1] == 200


def test_get_payment_method_with_missing_input():
    test_payer = PaymentUtil.create_payer()[0]
    with pytest.raises(TypeError):
        payment_method_v1_client.get_payment_method(payer_id=test_payer.id)


def test_create_get_delete_payment_method_with_payer_id_and_payment_method_id():
    # step 1: create a payment method using payer_id
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=test_payer.id
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using payer_id and payment_method_id
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment method using payer_id and payment_method_id
    delete_payment_method = payment_method_v1_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


def test_create_v1_and_get_v0_payment_method():
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=test_payer.id
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id,
        payment_method_id_type="payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0].id == payment_method[0].id


def test_create_v1_delete_v0_payment_method():
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=test_payer.id
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].id,
        payment_method_id_type="payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    retrieved_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert retrieved_payment_method[0].id == delete_payment_method[0].id
    assert retrieved_payment_method[0].deleted_at is not None


def test_create_v1_get_delete_v0_payment_method_with_payer_id_and_stripe_payment_method_id():
    # step 1: create a payment method using payer_id
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=PaymentUtil.get_payment_method_v1_request(
            payer_id=test_payer.id
        )
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using payer_id and stripe_payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0].deleted_at is None
    assert payment_method[0].id == get_payment_method[0].id

    # step 3: delete payment_method using payer_id and stripe_payment_method_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    retrieved_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[
            0
        ].payment_gateway_provider_details.payment_method_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert retrieved_payment_method[1] == 200
    assert retrieved_payment_method[0] == delete_payment_method[0]
    assert retrieved_payment_method[0].deleted_at is not None
