import logging

from payin_v1_client import (
    CreatePaymentMethodRequestV1,
    UpdatePayerRequestV1,
    DefaultPaymentMethodV1,
)

from tests.payin.v1 import payer_v1_client, payment_method_v1_client
from tests.payin.helper import PaymentUtil

logger = logging.getLogger(__name__)


def test_end_to_end():
    # Step 1: create payer object
    test_payer = PaymentUtil.create_payer()
    assert test_payer[1] == 201

    # Step 2: create payment_method
    create_payment_method_request = CreatePaymentMethodRequestV1(
        payer_id=test_payer[0].id,
        token="tok_visa",
        set_default=False,
        is_scanned=False,
        is_active=True,
        payment_gateway="stripe",
    )
    payment_method = payment_method_v1_client.create_payment_method_with_http_info(
        create_payment_method_request_v1=create_payment_method_request
    )
    assert payment_method[1] == 201
    assert payment_method[0].deleted_at is None
    assert payment_method[0].payer_id == test_payer[0].id

    # Step 3: set default payment_method
    default_payment_method = DefaultPaymentMethodV1(
        payment_method_id=payment_method[0].id
    )
    update_payer_request = UpdatePayerRequestV1(
        default_payment_method=default_payment_method
    )
    updated_payer = payer_v1_client.update_payer_default_payment_method_by_id_with_http_info(
        payer_id=test_payer[0].id, update_payer_request_v1=update_payer_request
    )
    assert updated_payer[1] == 200
    # verify default payment_method
    pay_providers_list = updated_payer[0].payment_gateway_provider_customers
    default_pm_id = None
    for pay_provider in pay_providers_list:
        if pay_provider.default_payment_method_id is not None:
            default_pm_id = pay_provider.default_payment_method_id
    assert (
        default_pm_id
        == payment_method[0].payment_gateway_provider_details.payment_method_id
    )

    # Step 4: get payment_method
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0].deleted_at is None

    # Step 5: delete payment_method
    delete_payment_method = payment_method_v1_client.delete_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0].deleted_at is not None

    # Step 6: verify payment_method to be deleted
    get_payment_method = payment_method_v1_client.get_payment_method_with_http_info(
        payment_method_id=payment_method[0].id
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0].deleted_at is not None

    # Step 7: verify default_payment_method of payer
    get_payer = payer_v1_client.get_payer_with_http_info(payer_id=test_payer[0].id)
    assert get_payer[1] == 200

    pay_providers_list = get_payer[0].payment_gateway_provider_customers
    default_pm_id = None
    for pay_provider in pay_providers_list:
        if pay_provider.default_payment_method_id is not None:
            default_pm_id = pay_provider.default_payment_method_id
    assert default_pm_id is None
