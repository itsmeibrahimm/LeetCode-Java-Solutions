import uuid
from datetime import timezone, datetime

import pytest
from asynctest import patch
from privacy import action_pb2, common_pb2

from app.commons.providers.stripe.stripe_models import (
    StripeDeleteCustomerResponse,
    Customer,
    InvoiceSettings,
)
from app.commons.types import CountryCode
from app.payin.core.payer.model import (
    DeletePayerSummary,
    DoorDashDomainRedact,
    RedactAction,
    StripeDomainRedact,
    StripeRedactAction,
)
from app.payin.core.payer.types import (
    DeletePayerRequestStatus,
    DeletePayerRedactingText,
)
from app.payin.repository.payer_repo import DeletePayerRequestDbEntity
from app.payin.repository.payment_method_repo import StripeCardDbEntity
from app.payin.tests.utils import (
    generate_delete_payer_request,
    FunctionMock,
    generate_pgp_payment_method,
    generate_cart_payment,
    generate_legacy_consumer_charge,
    generate_legacy_stripe_charge,
)


class TestDeletePayerProcessor:
    """
    Test external facing functions exposed by app/payin/core/payer/v0/processor.DeletePayerProcessor.
    """

    @pytest.fixture
    def delete_payer_request(self):
        delete_payer_summary = DeletePayerSummary(
            doordash_domain_redact=DoorDashDomainRedact(
                stripe_cards=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                ),
                stripe_charges=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                ),
                cart_payments=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                ),
            ),
            stripe_domain_redact=StripeDomainRedact(customers=[]),
        )
        return generate_delete_payer_request(summary=delete_payer_summary.json())

    @pytest.fixture
    def stripe_customer(self):
        return Customer(
            id="cus_1234567",
            object="customer",
            created=datetime.now(timezone.utc),
            currency="USD",
            invoice_settings=InvoiceSettings(default_payment_method=""),
            default_source="",
            description="",
            email="john.doe@gmail.com",
        )

    @pytest.mark.asyncio
    @patch("app.payin.core.payer.v0.processor.send_response", return_value=True)
    async def test_delete_payer_success(
        self,
        mock_send_response,
        delete_payer_request: DeletePayerRequestDbEntity,
        delete_payer_processor,
        stripe_customer,
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card = StripeCardDbEntity(
            id=uuid.uuid4(),
            stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            fingerprint="",
            last4="XXXX",
            dynamic_last4="XXXX",
            exp_month="01",
            exp_year="2020",
            type="Visa",
            active=True,
            country_of_origin="US",
            external_stripe_customer_id="cus_1234567",
        )
        stripe_cards = [stripe_card]
        cart_payment = generate_cart_payment()
        cart_payment.client_description = DeletePayerRedactingText.REDACTED
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_consumer_charge_ids = [legacy_consumer_charge.id]
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id
        )
        legacy_stripe_charge.description = DeletePayerRedactingText.REDACTED
        legacy_stripe_charges = [legacy_stripe_charge]
        stripe_delete_customer_response = StripeDeleteCustomerResponse(
            id=stripe_card.external_stripe_customer_id, object="customer", deleted=True
        )
        expected_summary = DeletePayerSummary(
            doordash_domain_redact=DoorDashDomainRedact(
                stripe_cards=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                stripe_charges=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                cart_payments=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
            ),
            stripe_domain_redact=StripeDomainRedact(
                customers=[
                    StripeRedactAction(
                        data_type="pii",
                        action="delete",
                        status=DeletePayerRequestStatus.SUCCEEDED,
                        stripe_customer_id=stripe_customer.id,
                        stripe_country=CountryCode.US,
                    )
                ]
            ),
        )
        updated_delete_payer_request = generate_delete_payer_request(
            summary=expected_summary.json()
        )
        delete_payer_processor.cart_payment_interface.update_cart_payments_remove_pii = FunctionMock(
            return_value=[cart_payment]
        )
        delete_payer_processor.payment_method_client.update_stripe_cards_remove_pii = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.payment_method_client.get_stripe_cards_for_consumer_id = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id = FunctionMock(
            return_value=legacy_consumer_charge_ids
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=legacy_stripe_charges
        )
        delete_payer_processor.legacy_payment_interface.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=legacy_stripe_charge
        )
        delete_payer_processor.payer_client.pgp_get_customer = FunctionMock(
            side_effect=[stripe_customer, None, None]
        )
        delete_payer_processor.payer_client.pgp_delete_customer = FunctionMock(
            return_value=stripe_delete_customer_response
        )
        delete_payer_processor.payer_client.pgp_get_customers = FunctionMock(
            return_value=[stripe_customer]
        )
        delete_payer_processor.payer_client.update_delete_payer_request = FunctionMock(
            return_value=updated_delete_payer_request
        )
        await delete_payer_processor.delete_payer(delete_payer_request)
        mock_send_response.assert_called_once_with(
            app_context=delete_payer_processor.app_context,
            log=delete_payer_processor.log,
            request_id=str(delete_payer_request.client_request_id),
            action_id=action_pb2.ActionId.CONSUMER_PAYMENTS_FORGET,
            status=common_pb2.StatusCode.COMPLETE,
            response=expected_summary.json(),
        )
        delete_payer_processor.payer_client.update_delete_payer_request.assert_called_with(
            delete_payer_request.client_request_id,
            DeletePayerRequestStatus.SUCCEEDED,
            expected_summary.json(),
            delete_payer_request.retry_count,
            True,
        )
        delete_payer_processor.payer_client.insert_delete_payer_request_metadata.assert_called_once_with(
            delete_payer_request.client_request_id,
            delete_payer_request.consumer_id,
            CountryCode.US,
            stripe_customer.email,
        )

    @pytest.mark.asyncio
    @patch("app.payin.core.payer.v0.processor.send_response", return_value=True)
    async def test_delete_payer_failed_to_remove_pii_stripe_cards(
        self,
        mock_send_response,
        delete_payer_request: DeletePayerRequestDbEntity,
        delete_payer_processor,
        stripe_customer,
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card = StripeCardDbEntity(
            id=uuid.uuid4(),
            stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            fingerprint="",
            last4="1234",
            dynamic_last4="5678",
            exp_month="01",
            exp_year="2020",
            type="Visa",
            active=True,
            country_of_origin="US",
            external_stripe_customer_id="cus_1234567",
        )
        stripe_cards = [stripe_card]
        cart_payment = generate_cart_payment()
        cart_payment.client_description = DeletePayerRedactingText.REDACTED
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_consumer_charge_ids = [legacy_consumer_charge.id]
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id
        )
        legacy_stripe_charge.description = DeletePayerRedactingText.REDACTED
        legacy_stripe_charges = [legacy_stripe_charge]
        stripe_delete_customer_response = StripeDeleteCustomerResponse(
            id=stripe_card.external_stripe_customer_id, object="customer", deleted=True
        )
        expected_summary = DeletePayerSummary(
            doordash_domain_redact=DoorDashDomainRedact(
                stripe_cards=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                ),
                stripe_charges=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                cart_payments=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
            ),
            stripe_domain_redact=StripeDomainRedact(
                customers=[
                    StripeRedactAction(
                        data_type="pii",
                        action="delete",
                        status=DeletePayerRequestStatus.SUCCEEDED,
                        stripe_customer_id=stripe_customer.id,
                        stripe_country=CountryCode.US,
                    )
                ]
            ),
        )
        updated_delete_payer_request = generate_delete_payer_request(
            summary=expected_summary.json()
        )
        delete_payer_processor.cart_payment_interface.update_cart_payments_remove_pii = FunctionMock(
            return_value=[cart_payment]
        )
        delete_payer_processor.payment_method_client.update_stripe_cards_remove_pii = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.payment_method_client.get_stripe_cards_for_consumer_id = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id = FunctionMock(
            return_value=legacy_consumer_charge_ids
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=legacy_stripe_charges
        )
        delete_payer_processor.legacy_payment_interface.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=legacy_stripe_charge
        )
        delete_payer_processor.payer_client.pgp_get_customer = FunctionMock(
            side_effect=[stripe_customer, None, None]
        )
        delete_payer_processor.payer_client.pgp_delete_customer = FunctionMock(
            return_value=stripe_delete_customer_response
        )
        delete_payer_processor.payer_client.pgp_get_customers = FunctionMock(
            return_value=[stripe_customer]
        )
        delete_payer_processor.payer_client.update_delete_payer_request = FunctionMock(
            return_value=updated_delete_payer_request
        )
        await delete_payer_processor.delete_payer(delete_payer_request)
        mock_send_response.assert_not_called()
        delete_payer_processor.payer_client.update_delete_payer_request.assert_called_with(
            delete_payer_request.client_request_id,
            DeletePayerRequestStatus.IN_PROGRESS,
            expected_summary.json(),
            delete_payer_request.retry_count + 1,
            delete_payer_request.acknowledged,
        )
        delete_payer_processor.payer_client.insert_delete_payer_request_metadata.assert_called_once_with(
            delete_payer_request.client_request_id,
            delete_payer_request.consumer_id,
            CountryCode.US,
            stripe_customer.email,
        )

    @pytest.mark.asyncio
    @patch("app.payin.core.payer.v0.processor.send_response", return_value=True)
    async def test_delete_payer_failed_to_remove_pii_stripe_charges(
        self,
        mock_send_response,
        delete_payer_request: DeletePayerRequestDbEntity,
        delete_payer_processor,
        stripe_customer,
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card = StripeCardDbEntity(
            id=uuid.uuid4(),
            stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            fingerprint="",
            last4="XXXX",
            dynamic_last4="XXXX",
            exp_month="01",
            exp_year="2020",
            type="Visa",
            active=True,
            country_of_origin="US",
            external_stripe_customer_id="cus_1234567",
        )
        stripe_cards = [stripe_card]
        cart_payment = generate_cart_payment()
        cart_payment.client_description = DeletePayerRedactingText.REDACTED
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_consumer_charge_ids = [legacy_consumer_charge.id]
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id
        )
        legacy_stripe_charges = [legacy_stripe_charge]
        stripe_delete_customer_response = StripeDeleteCustomerResponse(
            id=stripe_card.external_stripe_customer_id, object="customer", deleted=True
        )
        expected_summary = DeletePayerSummary(
            doordash_domain_redact=DoorDashDomainRedact(
                stripe_cards=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                stripe_charges=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                ),
                cart_payments=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
            ),
            stripe_domain_redact=StripeDomainRedact(
                customers=[
                    StripeRedactAction(
                        data_type="pii",
                        action="delete",
                        status=DeletePayerRequestStatus.SUCCEEDED,
                        stripe_customer_id=stripe_customer.id,
                        stripe_country=CountryCode.US,
                    )
                ]
            ),
        )
        updated_delete_payer_request = generate_delete_payer_request(
            summary=expected_summary.json()
        )
        delete_payer_processor.cart_payment_interface.update_cart_payments_remove_pii = FunctionMock(
            return_value=[cart_payment]
        )
        delete_payer_processor.payment_method_client.update_stripe_cards_remove_pii = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.payment_method_client.get_stripe_cards_for_consumer_id = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id = FunctionMock(
            return_value=legacy_consumer_charge_ids
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=legacy_stripe_charges
        )
        delete_payer_processor.legacy_payment_interface.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=legacy_stripe_charge
        )
        delete_payer_processor.payer_client.pgp_get_customer = FunctionMock(
            side_effect=[stripe_customer, None, None]
        )
        delete_payer_processor.payer_client.pgp_delete_customer = FunctionMock(
            return_value=stripe_delete_customer_response
        )
        delete_payer_processor.payer_client.pgp_get_customers = FunctionMock(
            return_value=[stripe_customer]
        )
        delete_payer_processor.payer_client.update_delete_payer_request = FunctionMock(
            return_value=updated_delete_payer_request
        )
        await delete_payer_processor.delete_payer(delete_payer_request)
        mock_send_response.assert_not_called()
        delete_payer_processor.payer_client.update_delete_payer_request.assert_called_with(
            delete_payer_request.client_request_id,
            DeletePayerRequestStatus.IN_PROGRESS,
            expected_summary.json(),
            delete_payer_request.retry_count + 1,
            delete_payer_request.acknowledged,
        )
        delete_payer_processor.payer_client.insert_delete_payer_request_metadata.assert_called_once_with(
            delete_payer_request.client_request_id,
            delete_payer_request.consumer_id,
            CountryCode.US,
            stripe_customer.email,
        )

    @pytest.mark.asyncio
    @patch("app.payin.core.payer.v0.processor.send_response", return_value=True)
    async def test_delete_payer_failed_to_remove_pii_cart_payments(
        self,
        mock_send_response,
        delete_payer_request: DeletePayerRequestDbEntity,
        delete_payer_processor,
        stripe_customer,
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card = StripeCardDbEntity(
            id=uuid.uuid4(),
            stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            fingerprint="",
            last4="XXXX",
            dynamic_last4="XXXX",
            exp_month="01",
            exp_year="2020",
            type="Visa",
            active=True,
            country_of_origin="US",
            external_stripe_customer_id="cus_1234567",
        )
        stripe_cards = [stripe_card]
        cart_payment = generate_cart_payment()
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_consumer_charge_ids = [legacy_consumer_charge.id]
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id
        )
        legacy_stripe_charge.description = DeletePayerRedactingText.REDACTED
        legacy_stripe_charges = [legacy_stripe_charge]
        stripe_delete_customer_response = StripeDeleteCustomerResponse(
            id=stripe_card.external_stripe_customer_id, object="customer", deleted=True
        )
        expected_summary = DeletePayerSummary(
            doordash_domain_redact=DoorDashDomainRedact(
                stripe_cards=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                stripe_charges=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                cart_payments=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                ),
            ),
            stripe_domain_redact=StripeDomainRedact(
                customers=[
                    StripeRedactAction(
                        data_type="pii",
                        action="delete",
                        status=DeletePayerRequestStatus.SUCCEEDED,
                        stripe_customer_id=stripe_customer.id,
                        stripe_country=CountryCode.US,
                    )
                ]
            ),
        )
        updated_delete_payer_request = generate_delete_payer_request(
            summary=expected_summary.json()
        )
        delete_payer_processor.cart_payment_interface.update_cart_payments_remove_pii = FunctionMock(
            return_value=[cart_payment]
        )
        delete_payer_processor.payment_method_client.update_stripe_cards_remove_pii = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.payment_method_client.get_stripe_cards_for_consumer_id = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id = FunctionMock(
            return_value=legacy_consumer_charge_ids
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=legacy_stripe_charges
        )
        delete_payer_processor.legacy_payment_interface.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=legacy_stripe_charge
        )
        delete_payer_processor.payer_client.pgp_get_customer = FunctionMock(
            side_effect=[stripe_customer, None, None]
        )
        delete_payer_processor.payer_client.pgp_delete_customer = FunctionMock(
            return_value=stripe_delete_customer_response
        )
        delete_payer_processor.payer_client.pgp_get_customers = FunctionMock(
            return_value=[stripe_customer]
        )
        delete_payer_processor.payer_client.update_delete_payer_request = FunctionMock(
            return_value=updated_delete_payer_request
        )
        await delete_payer_processor.delete_payer(delete_payer_request)
        mock_send_response.assert_not_called()
        delete_payer_processor.payer_client.update_delete_payer_request.assert_called_with(
            delete_payer_request.client_request_id,
            DeletePayerRequestStatus.IN_PROGRESS,
            expected_summary.json(),
            delete_payer_request.retry_count + 1,
            delete_payer_request.acknowledged,
        )
        delete_payer_processor.payer_client.insert_delete_payer_request_metadata.assert_called_once_with(
            delete_payer_request.client_request_id,
            delete_payer_request.consumer_id,
            CountryCode.US,
            stripe_customer.email,
        )

    @pytest.mark.asyncio
    @patch("app.payin.core.payer.v0.processor.send_response", return_value=True)
    async def test_delete_payer_failed_to_delete_customer(
        self,
        mock_send_response,
        delete_payer_request: DeletePayerRequestDbEntity,
        delete_payer_processor,
        stripe_customer,
    ):
        pgp_payment_method_list = [generate_pgp_payment_method()]
        stripe_card = StripeCardDbEntity(
            id=uuid.uuid4(),
            stripe_id=pgp_payment_method_list[0].pgp_resource_id,
            fingerprint="",
            last4="XXXX",
            dynamic_last4="XXXX",
            exp_month="01",
            exp_year="2020",
            type="Visa",
            active=True,
            country_of_origin="US",
            external_stripe_customer_id="cus_1234567",
        )
        stripe_cards = [stripe_card]
        cart_payment = generate_cart_payment()
        cart_payment.client_description = DeletePayerRedactingText.REDACTED
        legacy_consumer_charge = generate_legacy_consumer_charge()
        legacy_consumer_charge_ids = [legacy_consumer_charge.id]
        legacy_stripe_charge = generate_legacy_stripe_charge(
            charge_id=legacy_consumer_charge.id
        )
        legacy_stripe_charge.description = DeletePayerRedactingText.REDACTED
        legacy_stripe_charges = [legacy_stripe_charge]
        stripe_delete_customer_response = StripeDeleteCustomerResponse(
            id=stripe_card.external_stripe_customer_id, object="customer", deleted=False
        )
        expected_summary = DeletePayerSummary(
            doordash_domain_redact=DoorDashDomainRedact(
                stripe_cards=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                stripe_charges=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
                cart_payments=RedactAction(
                    data_type="pii",
                    action="obfuscate",
                    status=DeletePayerRequestStatus.SUCCEEDED,
                ),
            ),
            stripe_domain_redact=StripeDomainRedact(
                customers=[
                    StripeRedactAction(
                        data_type="pii",
                        action="delete",
                        status=DeletePayerRequestStatus.IN_PROGRESS,
                        stripe_customer_id=stripe_customer.id,
                        stripe_country=CountryCode.US,
                    )
                ]
            ),
        )
        updated_delete_payer_request = generate_delete_payer_request(
            summary=expected_summary.json()
        )
        delete_payer_processor.cart_payment_interface.update_cart_payments_remove_pii = FunctionMock(
            return_value=[cart_payment]
        )
        delete_payer_processor.payment_method_client.update_stripe_cards_remove_pii = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.payment_method_client.get_stripe_cards_for_consumer_id = FunctionMock(
            return_value=stripe_cards
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_consumer_charge_ids_by_consumer_id = FunctionMock(
            return_value=legacy_consumer_charge_ids
        )
        delete_payer_processor.legacy_payment_interface.get_legacy_stripe_charges_by_charge_id = FunctionMock(
            return_value=legacy_stripe_charges
        )
        delete_payer_processor.legacy_payment_interface.update_legacy_stripe_charge_remove_pii = FunctionMock(
            return_value=legacy_stripe_charge
        )
        delete_payer_processor.payer_client.pgp_get_customer = FunctionMock(
            side_effect=[stripe_customer, None, None]
        )
        delete_payer_processor.payer_client.pgp_delete_customer = FunctionMock(
            return_value=stripe_delete_customer_response
        )
        delete_payer_processor.payer_client.pgp_get_customers = FunctionMock(
            return_value=[stripe_customer]
        )
        delete_payer_processor.payer_client.update_delete_payer_request = FunctionMock(
            return_value=updated_delete_payer_request
        )
        await delete_payer_processor.delete_payer(delete_payer_request)
        mock_send_response.assert_not_called()
        delete_payer_processor.payer_client.update_delete_payer_request.assert_called_with(
            delete_payer_request.client_request_id,
            DeletePayerRequestStatus.IN_PROGRESS,
            expected_summary.json(),
            delete_payer_request.retry_count + 1,
            delete_payer_request.acknowledged,
        )
        delete_payer_processor.payer_client.insert_delete_payer_request_metadata.assert_called_once_with(
            delete_payer_request.client_request_id,
            delete_payer_request.consumer_id,
            CountryCode.US,
            stripe_customer.email,
        )
