import logging

from . import payin_client_pulse
from .utils import PaymentUtil

logger = logging.getLogger(__name__)


def test_end_to_end():
    # step 1: create payer object
    test_payer = PaymentUtil.create_payer()
    assert test_payer[1] == 201

    # step 2: create payment_method
    payment_method = payin_client_pulse.create_payment_method_api_v1_payment_methods_post_with_http_info(
        create_payment_method_request={
            "payer_id": test_payer[0]["id"],
            "payment_gateway": "stripe",
            "token": "tok_visa",
        }
    )
    assert payment_method[1] == 201
    assert payment_method[0]["deleted_at"] is None

    # step 3: update payment_method of payer object
    updated_payer = payin_client_pulse.update_payer_api_v1_payers_payer_id_patch_with_http_info(
        payer_id=test_payer[0]["id"],
        update_payer_request={"default_payment_method": payment_method[0]},
    )
    assert updated_payer[1] == 200
    # verify default payment_method
    pay_providers_list = updated_payer[0]["payment_gateway_provider_customers"]
    default_payment_method_id = None
    # todo - test for default_payment_method using multiple payment methods
    for pay_provider in pay_providers_list:
        if pay_provider["default_payment_method_id"] is not None:
            default_payment_method_id = pay_provider["default_payment_method_id"]
    assert (
        default_payment_method_id
        == payment_method[0]["card"]["payment_provider_card_id"]
    )

    # step 4: get payment_method
    get_payment_method = payin_client_pulse.get_payment_method_api_v1_payment_methods_payer_id_payment_method_id_get_with_http_info(
        payer_id=test_payer[0]["id"], payment_method_id=payment_method[0]["id"]
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == payment_method[0]
    assert get_payment_method[0]["deleted_at"] is None

    # step 5: delete payment_method
    delete_payment_method = payin_client_pulse.delete_payment_method_api_v1_payment_methods_payer_id_payment_method_id_delete_with_http_info(
        payer_id=test_payer[0]["id"], payment_method_id=payment_method[0]["id"]
    )
    assert delete_payment_method[1] == 200
    assert delete_payment_method[0] != get_payment_method[0]
    assert delete_payment_method[0]["deleted_at"] is not None

    # step 6: verify payment_method to be deleted
    get_payment_method = payin_client_pulse.get_payment_method_api_v1_payment_methods_payer_id_payment_method_id_get_with_http_info(
        payer_id=test_payer[0]["id"], payment_method_id=payment_method[0]["id"]
    )
    assert get_payment_method[1] == 200
    assert get_payment_method[0] == delete_payment_method[0]
    assert get_payment_method[0]["deleted_at"] is not None

    # step 7: verify default_payment_method of payer
    get_payer = payin_client_pulse.get_payer_api_v1_payers_payer_id_get_with_http_info(
        payer_id=test_payer[0]["id"]
    )
    assert get_payer[1] == 200

    pay_providers_list = get_payer[0]["payment_gateway_provider_customers"]
    default_pm_id = None
    for pay_provider in pay_providers_list:
        if pay_provider["default_payment_method_id"] is not None:
            default_pm_id = pay_provider["default_payment_method_id"]
    assert default_pm_id is None
