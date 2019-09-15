import logging
import pytest

from . import payment_method_v0_client, payment_method_v1_client
from payin_v0_client import (
    ApiException,
)  # use the ApiException of same version client whose ApiClient has been used
from .utils import PaymentUtil, StripeUtil

logger = logging.getLogger(__name__)


def test_create_payment_method_with_invalid_input():
    try:
        payment_method_v1_client.create_payment_method_with_http_info(
            create_payment_method_request={
                "payer_id": [123],
                "payment_gateway": "stripe",
                "token": "tok_visa",
            }
        )
    except ApiException as e:
        assert e.status == 422


def test_create_payment_method_with_missing_payer_id():
    try:
        payment_method_v1_client.create_payment_method_with_http_info(
            create_payment_method_request={
                "payment_gateway": "stripe",
                "token": "tok_visa",
            }
        )
    except ApiException as e:
        assert e.status == 422


def test_get_payment_method_with_invalid_input():
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payer_id": test_payer.id,
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    try:
        payment_method_v1_client.get_payment_method(
            payer_id=[123], payment_method_id=payment_method[0].id
        )
    except ApiException as e:
        # Fixme - should raise a 400 bad_request error here, but raising a 500
        assert e.status == 500


def test_get_payment_method_with_missing_input():
    test_payer = PaymentUtil.create_payer()[0]
    with pytest.raises(TypeError):
        payment_method_v1_client.get_payment_method(payer_id=test_payer.id)


# test payment_methods with payer_id
def test_create_get_delete_payment_method_with_payer_id_and_payment_method_id():
    # step 1: create a payment method using payer_id
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payer_id": test_payer.id,
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using payer_id and payment_method_id
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payer_id=test_payer.id, payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment method using payer_id and payment_method_id
    delete_payment_method = payment_method_v1_client.delete_payment_method_with_http_info(
        payer_id=test_payer.id, payment_method_id=payment_method[0].id
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payer_id=test_payer.id, payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


@pytest.mark.skip(reason="need to update client lib to change to v0 api")
def test_create_get_delete_payment_method_with_payer_id_and_stripe_payment_method_id():
    # step 1: create a payment method using payer_id
    test_payer = PaymentUtil.create_payer()[0]
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payer_id": test_payer.id,
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using payer_id and stripe_payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using payer_id and stripe_payment_method_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


@pytest.mark.skip(reason="cannot connect to StripeCard table")
def test_create_get_delete_payment_method_with_payer_id_and_stripe_card_serial_id():
    # step 1: create StripeCard and attach to payer
    # test_payer = PaymentUtil.create_payer()[0]

    # step 2: get payment_method using payer_id and stripe_card_serial_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert get_payment_method[1] == 200
    # assert get_payment_method[0] == payment_method
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using payer_id and stripe_card_serial_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


# test payment_methods with stripe_customer_id
@pytest.mark.skip(reason="test Stripe key not setup yet in pulse")
def test_create_get_delete_payment_method_with_stripe_customer_id_and_payment_method_id():
    # step 1: create a payment method using stripe_customer_id
    stripe_cus = StripeUtil.create_stripe_customer()
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payment_gateway": "stripe",
            "token": "tok_visa",
            "legacy_payment_info": {"stripe_customer_id": stripe_cus["id"]},
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using stripe_customer_id and payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment method using stripe_customer_id and payment_method_id
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


@pytest.mark.skip(reason="test Stripe key not setup yet in pulse")
def test_create_get_delete_payment_method_with_stripe_customer_id_and_stripe_payment_method_id():
    # step 1: create a payment method using stripe_customer_id
    stripe_cus = StripeUtil.create_stripe_customer()
    # todo - create_payment_method with v0 version for legacy fields
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payment_gateway": "stripe",
            "token": "tok_visa",
            "legacy_payment_info": {"stripe_customer_id": stripe_cus["id"]},
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment method using stripe_customer_id and stripe_payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_id and stripe_payment_method_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify that payment_method has been deleted
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


@pytest.mark.skip(
    reason="cannot connect to StripeCard table and test Stripe key not setup yet"
)
def test_create_get_delete_payment_method_with_stripe_customer_id_and_stripe_card_serial_id():
    # step 1: create StripeCard and attach to StripeCustomer
    # stripe_cus = StripeUtil.create_stripe_customer()

    # step 2: get payment_method using stripe_customer_id and stripe_card_serial_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert get_payment_method[1] == 200
    # assert get_payment_method[0] == payment_method
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_id and stripe_card_serial_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert get_payment_method[1] == 200
    # assert get_payment_method[0] == payment_method
    assert get_payment_method[0].deleted_at is not None


# test payment_methods with stripe_customer_serial_id
@pytest.mark.skip(reason="test Stripe key not setup yet in pulse")
def test_create_get_delete_payment_method_using_stripe_customer_serial_id_and_payment_method_id():
    # step 1: create a payment method using stripe_customer_id
    stripe_cus = StripeUtil.create_stripe_customer()
    # todo - create_payment_method with v0 version for legacy fields
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payment_gateway": "stripe",
            "token": "tok_visa",
            "legacy_payment_info": {"stripe_customer_id": stripe_cus["id"]},
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment_method using stripe_customer_serial_id and payment_method_id
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_serial_id and payment_method_id
    delete_payment_method = payment_method_v1_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method.id
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


@pytest.mark.skip(reason="test Stripe key not setup yet in pulse")
def test_create_get_delete_payment_method_using_stripe_customer_serial_id_and_stripe_payment_method_id():
    # step 1: create a payment method using stripe_customer_id
    stripe_cus = StripeUtil.create_stripe_customer()
    # todo - create_payment_method with v0 version for legacy fields
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request={
            "payment_gateway": "stripe",
            "token": "tok_visa",
            "legacy_payment_info": {"stripe_customer_id": stripe_cus["id"]},
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None

    # step 2: get payment_method using stripe_customer_serial_id and stripe_payment_method_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method.card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_serial_id and stripe_payment_method_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method.card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id=payment_method.card.payment_provider_card_id,
        payment_method_id_type="stripe_payment_method_id",
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None


@pytest.mark.skip(
    reason="cannot connect to StripeCard table and test Stripe key not setup yet"
)
def test_create_get_delete_payment_method_using_stripe_customer_serial_id_and_stripe_card_serial_id():
    # step 1: create a StripeCard and attach it to StripeCustomer
    # stripe_cus = StripeUtil.create_stripe_customer()

    # step 2: get payment_method using stripe_customer_serial_id and stripe_card_serial_id
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert get_payment_method[1] == 200
    # assert get_payment_method0] == payment_method
    assert get_payment_method[0].deleted_at is None

    # step 3: delete payment_method using stripe_customer_serial_id and stripe_card_serial_id
    delete_payment_method = payment_method_v0_client.delete_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # step 4: verify payment_method to be deleted
    get_payment_method = payment_method_v0_client.get_payment_method_with_http_info(
        payment_method_id="", payment_method_id_type="stripe_card_serial_id"
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None
