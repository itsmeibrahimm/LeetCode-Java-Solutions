from datetime import datetime, timezone
from typing import cast
from uuid import uuid4, UUID

import pytest

from app.commons.providers.stripe import stripe_models as models
from app.commons.types import CountryCode, PgpCode, LegacyCountryId, Currency
from app.payin.core.cart_payment.types import LegacyStripeChargeStatus
from app.payin.core.payer.model import (
    DoorDashDomainRedact,
    DeletePayerSummary,
    RedactAction,
    StripeDomainRedact,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.core.payer.v0.processor import DeletePayerProcessor
from app.payin.models.maindb import consumer_charges, stripe_charges, stripe_cards
from app.payin.models.paymentdb import (
    delete_payer_requests,
    payers,
    cart_payments,
    pgp_payment_methods,
)
from app.payin.repository.cart_payment_repo import CartPaymentRepository
from app.payin.repository.payer_repo import (
    PayerRepository,
    DeletePayerRequestDbEntity,
    InsertPayerInput,
)
from app.payin.repository.payment_method_repo import (
    PaymentMethodRepository,
    InsertPgpPaymentMethodInput,
    InsertStripeCardInput,
)


class TestDeletePayerProcessor:
    pytestmark = [pytest.mark.asyncio, pytest.mark.external, pytest.mark.integration]

    @pytest.fixture
    def delete_payer_summary(self):
        return DeletePayerSummary(
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
            stripe_domain_redact=StripeDomainRedact(
                customer=RedactAction(
                    data_type="pii",
                    action="delete",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                )
            ),
        )

    @pytest.fixture
    async def delete_payer_request(
        self, payer_repository: PayerRepository, delete_payer_summary
    ):
        uuid = uuid4()
        yield await payer_repository.insert_delete_payer_request(
            DeletePayerRequestDbEntity(
                id=uuid,
                client_request_id=uuid,
                consumer_id=2,
                payer_id=None,
                status=DeletePayerRequestStatus.IN_PROGRESS.value,
                summary=delete_payer_summary.json(),
                retry_count=0,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                acknowledged=False,
            )
        )
        await payer_repository.payment_database.master().execute(
            delete_payer_requests.table.delete().where(delete_payer_requests.id == uuid)
        )

    @pytest.fixture
    async def payer(self, payer_repository: PayerRepository):
        uuid = uuid4()
        yield await payer_repository.insert_payer(
            InsertPayerInput(id=uuid, country=CountryCode.US)
        )
        await payer_repository.payment_database.master().execute(
            payers.table.delete().where(payers.id == uuid)
        )

    @pytest.fixture
    async def cart_payment(
        self, payer, pgp_payment_method, cart_payment_repository: CartPaymentRepository
    ):
        uuid = uuid4()
        yield await cart_payment_repository.insert_cart_payment(
            id=uuid,
            payer_id=cast(UUID, payer.id),
            amount_original=99,
            amount_total=100,
            client_description="John Doe ordered donuts",
            reference_id="99",
            reference_type="88",
            delay_capture=False,
            metadata=None,
            legacy_consumer_id=2,
            legacy_stripe_card_id=1,
            legacy_provider_customer_id=None,
            legacy_provider_card_id=pgp_payment_method.pgp_resource_id,
        )
        await cart_payment_repository.payment_database.master().execute(
            cart_payments.table.delete().where(cart_payments.id == uuid)
        )

    @pytest.fixture
    async def pgp_payment_method(
        self, payment_method_repository: PaymentMethodRepository
    ):
        uuid = uuid4()
        yield await payment_method_repository.insert_pgp_payment_method(
            InsertPgpPaymentMethodInput(
                id=uuid,
                pgp_code=PgpCode.STRIPE,
                pgp_resource_id="card_lKPdMYINpftZIxF",
                created_at=datetime.now(timezone.utc),
            )
        )
        await payment_method_repository.payment_database.master().execute(
            pgp_payment_methods.table.delete().where(pgp_payment_methods.id == uuid)
        )

    @pytest.fixture
    async def stripe_card(
        self,
        customer,
        pgp_payment_method,
        payment_method_repository: PaymentMethodRepository,
    ):
        stripe_card = await payment_method_repository.insert_stripe_card(
            InsertStripeCardInput(
                stripe_id=pgp_payment_method.pgp_resource_id,
                consumer_id=2,
                fingerprint="fingerprint",
                last4="1234",
                dynamic_last4="4621",
                exp_month="03",
                exp_year="2020",
                type="visa",
                active=True,
                external_stripe_customer_id=customer.stripe_id,
            )
        )
        sid = stripe_card.id
        yield stripe_card
        await payment_method_repository.main_database.master().execute(
            stripe_cards.table.delete().where(stripe_cards.id == sid)
        )

    @pytest.fixture
    async def consumer_charge(self, cart_payment_repository: CartPaymentRepository):
        uuid = uuid4()
        yield await cart_payment_repository.insert_legacy_consumer_charge(
            target_ct_id=1,
            target_id=2,
            consumer_id=2,  # Use of pre-seeded consumer to satisfy FK constraint
            idempotency_key=str(uuid),
            is_stripe_connect_based=False,
            country_id=LegacyCountryId.US,
            currency=Currency.USD,
            stripe_customer_id=None,
            total=800,
            original_total=800,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await cart_payment_repository.main_database.master().execute(
            consumer_charges.table.delete().where(
                consumer_charges.idempotency_key == str(uuid)
            )
        )

    @pytest.fixture
    async def stripe_charge(
        self,
        cart_payment_repository: CartPaymentRepository,
        consumer_charge,
        stripe_card,
    ):
        uuid = uuid4()
        yield await cart_payment_repository.insert_legacy_stripe_charge(
            stripe_id="ch_C5BHUheWL33OHF",
            card_id=stripe_card.id,
            charge_id=consumer_charge.id,
            amount=consumer_charge.total,
            amount_refunded=0,
            currency=Currency.USD,
            status=LegacyStripeChargeStatus.SUCCEEDED,
            idempotency_key=str(uuid),
            additional_payment_info="{'test_key': 'test_value'}",
            description="John Doe ordered donuts",
            error_reason="",
        )
        await cart_payment_repository.main_database.master().execute(
            stripe_charges.table.delete().where(
                stripe_charges.idempotency_key == str(uuid)
            )
        )

    @pytest.fixture
    async def customer(self, stripe_async_client):
        return await stripe_async_client.create_customer(
            country=models.CountryCode.US,
            request=models.StripeCreateCustomerRequest(
                email="john.doe@gmail.com", description="john doe", country="US"
            ),
        )

    async def test_delete_payer_with_card_success(
        self,
        delete_payer_processor: DeletePayerProcessor,
        delete_payer_request: DeletePayerRequestDbEntity,
        payer_client: PayerClient,
        stripe_card,
        stripe_charge,
        cart_payment,
    ):
        await delete_payer_processor.delete_payer(delete_payer_request)
        updated_delete_payer_requests = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=delete_payer_request.client_request_id
        )
        assert len(updated_delete_payer_requests) == 1
        updated_delete_payer_request = updated_delete_payer_requests[0]
        delete_payer_summary = DeletePayerSummary.parse_raw(
            updated_delete_payer_request.summary
        )
        assert (
            delete_payer_summary.doordash_domain_redact.stripe_cards.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            delete_payer_summary.doordash_domain_redact.stripe_charges.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            delete_payer_summary.doordash_domain_redact.cart_payments.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            delete_payer_summary.stripe_domain_redact.customer.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert updated_delete_payer_request.status == DeletePayerRequestStatus.SUCCEEDED
        assert updated_delete_payer_request.acknowledged is True

    async def test_delete_payer_without_card_success(
        self,
        delete_payer_processor: DeletePayerProcessor,
        delete_payer_request: DeletePayerRequestDbEntity,
        payer_client: PayerClient,
    ):
        await delete_payer_processor.delete_payer(delete_payer_request)
        updated_delete_payer_requests = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=delete_payer_request.client_request_id
        )
        assert len(updated_delete_payer_requests) == 1
        updated_delete_payer_request = updated_delete_payer_requests[0]
        delete_payer_summary = DeletePayerSummary.parse_raw(
            updated_delete_payer_request.summary
        )
        assert (
            delete_payer_summary.doordash_domain_redact.stripe_cards.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            delete_payer_summary.doordash_domain_redact.stripe_charges.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            delete_payer_summary.doordash_domain_redact.cart_payments.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            delete_payer_summary.stripe_domain_redact.customer.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert updated_delete_payer_request.status == DeletePayerRequestStatus.SUCCEEDED
        assert updated_delete_payer_request.acknowledged is True

    async def test_delete_payer_with_card_failure(
        self,
        delete_payer_processor: DeletePayerProcessor,
        payer_client: PayerClient,
        payer_repository: PayerRepository,
    ):
        delete_payer_summary = DeletePayerSummary(
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
                customer=RedactAction(
                    data_type="pii",
                    action="delete",
                    status=DeletePayerRequestStatus.IN_PROGRESS,
                )
            ),
        )
        uuid = uuid4()
        delete_payer_request = await payer_repository.insert_delete_payer_request(
            DeletePayerRequestDbEntity(
                id=uuid,
                client_request_id=uuid,
                consumer_id=1,
                payer_id=None,
                status=DeletePayerRequestStatus.IN_PROGRESS.value,
                summary=delete_payer_summary.json(),
                retry_count=5,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                acknowledged=False,
            )
        )

        await delete_payer_processor.delete_payer(delete_payer_request)
        updated_delete_payer_requests = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=delete_payer_request.client_request_id
        )
        assert len(updated_delete_payer_requests) == 1
        updated_delete_payer_request = updated_delete_payer_requests[0]
        updated_delete_payer_summary = DeletePayerSummary.parse_raw(
            updated_delete_payer_request.summary
        )
        assert (
            updated_delete_payer_request.status == DeletePayerRequestStatus.IN_PROGRESS
        )
        assert (
            updated_delete_payer_summary.doordash_domain_redact.stripe_cards.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            updated_delete_payer_summary.doordash_domain_redact.stripe_charges.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            updated_delete_payer_summary.doordash_domain_redact.cart_payments.status
            == DeletePayerRequestStatus.SUCCEEDED
        )
        assert (
            updated_delete_payer_summary.stripe_domain_redact.customer.status
            == DeletePayerRequestStatus.IN_PROGRESS
        )
        assert updated_delete_payer_request.acknowledged is False

        await payer_repository.payment_database.master().execute(
            delete_payer_requests.table.delete().where(delete_payer_requests.id == uuid)
        )
