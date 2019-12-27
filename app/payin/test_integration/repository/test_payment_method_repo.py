from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.commons.types import CountryCode, PgpCode
from app.payin.core.types import PayerReferenceIdType
from app.payin.repository.payer_repo import (
    PayerDbEntity,
    PayerRepository,
    InsertPayerInput,
)
from app.payin.repository.payment_method_repo import (
    PaymentMethodRepository,
    PaymentMethodDbEntity,
    InsertPaymentMethodInput,
    InsertPgpPaymentMethodInput,
    GetPgpPaymentMethodByPgpResourceIdInput,
    GetPgpPaymentMethodByIdInput,
    GetPgpPaymentMethodByPaymentMethodId,
    DeletePgpPaymentMethodByIdSetInput,
    DeletePgpPaymentMethodByIdWhereInput,
    InsertStripeCardInput,
    ListStripeCardDbEntitiesByStripeCustomerId,
    ListPgpPaymentMethodByStripeCardId,
)


@pytest.fixture
async def payer(payer_repository: PayerRepository) -> PayerDbEntity:
    insert_payer_input = InsertPayerInput(
        id=uuid4(),
        payer_reference_id_type=PayerReferenceIdType.DD_DRIVE_STORE_ID,
        country=CountryCode.US,
    )
    return await payer_repository.insert_payer(insert_payer_input)


@pytest.fixture
async def payment_method(
    payer: PayerDbEntity, payment_method_repository: PaymentMethodRepository
) -> PaymentMethodDbEntity:
    now = datetime.now()
    insert_payment_method_input = InsertPaymentMethodInput(
        id=uuid4(), payer_id=payer.id, created_at=now, updated_at=now
    )
    return await payment_method_repository.insert_payment_method(
        pm_input=insert_payment_method_input
    )


class TestPaymentMethodRepository:
    pytestmark = [pytest.mark.asyncio]

    async def test_insert_pgp_payment_method(
        self,
        payment_method: PaymentMethodDbEntity,
        payment_method_repository: PaymentMethodRepository,
    ):
        insert_pgp_payment_method_input = InsertPgpPaymentMethodInput(
            id=uuid4(),
            payer_id=payment_method.payer_id,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=str(uuid4()),
            payment_method_id=payment_method.id,
            created_at=datetime.now(timezone.utc),
        )
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=insert_pgp_payment_method_input
        )
        assert pgp_payment_method is not None
        assert pgp_payment_method.payer_id == payment_method.payer_id
        assert pgp_payment_method.payment_method_id == payment_method.id
        assert (
            pgp_payment_method.pgp_resource_id
            == insert_pgp_payment_method_input.pgp_resource_id
        )

    async def test_insert_payment_method(
        self, payer: PayerDbEntity, payment_method_repository: PaymentMethodRepository
    ):
        now = datetime.now()
        insert_payment_method_input = InsertPaymentMethodInput(
            id=uuid4(), payer_id=payer.id, created_at=now, updated_at=now
        )
        payment_method = await payment_method_repository.insert_payment_method(
            pm_input=insert_payment_method_input
        )
        assert payment_method is not None
        assert payment_method.payer_id == insert_payment_method_input.payer_id

    async def test_get_pgp_payment_method_by_pgp_resource_id(
        self,
        payment_method: PaymentMethodDbEntity,
        payment_method_repository: PaymentMethodRepository,
    ):
        created_at = datetime.now(timezone.utc)
        insert_pgp_payment_method_input = InsertPgpPaymentMethodInput(
            id=uuid4(),
            payer_id=payment_method.payer_id,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=str(uuid4()),
            payment_method_id=payment_method.id,
            created_at=created_at,
        )
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=insert_pgp_payment_method_input
        )
        assert pgp_payment_method is not None
        input = GetPgpPaymentMethodByPgpResourceIdInput(
            pgp_resource_id=insert_pgp_payment_method_input.pgp_resource_id
        )
        get_pgp_payment_method = await payment_method_repository.get_pgp_payment_method_by_pgp_resource_id(
            input=input
        )
        assert get_pgp_payment_method is not None
        assert get_pgp_payment_method == pgp_payment_method

    async def test_get_pgp_payment_method_by_id(
        self,
        payment_method: PaymentMethodDbEntity,
        payment_method_repository: PaymentMethodRepository,
    ):
        created_at = datetime.now(timezone.utc)
        insert_pgp_payment_method_input = InsertPgpPaymentMethodInput(
            id=uuid4(),
            payer_id=payment_method.payer_id,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=str(uuid4()),
            payment_method_id=payment_method.id,
            created_at=created_at,
        )
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=insert_pgp_payment_method_input
        )
        assert pgp_payment_method is not None
        input = GetPgpPaymentMethodByIdInput(id=insert_pgp_payment_method_input.id)
        get_pgp_payment_method = await payment_method_repository.get_pgp_payment_method_by_id(
            input=input
        )
        assert get_pgp_payment_method is not None
        assert get_pgp_payment_method == pgp_payment_method

    async def test_get_pgp_payment_method_by_payment_id(
        self,
        payment_method: PaymentMethodDbEntity,
        payment_method_repository: PaymentMethodRepository,
    ):
        created_at = datetime.now(timezone.utc)
        insert_pgp_payment_method_input = InsertPgpPaymentMethodInput(
            id=uuid4(),
            payer_id=payment_method.payer_id,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=str(uuid4()),
            payment_method_id=payment_method.id,
            created_at=created_at,
        )
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=insert_pgp_payment_method_input
        )
        assert pgp_payment_method is not None
        input = GetPgpPaymentMethodByPaymentMethodId(
            id=insert_pgp_payment_method_input.payment_method_id
        )
        get_pgp_payment_method = await payment_method_repository.get_pgp_payment_method_by_payment_method_id(
            input=input
        )
        assert get_pgp_payment_method is not None
        assert get_pgp_payment_method == pgp_payment_method

    async def test_delete_pgp_payment_method_by_id(
        self,
        payment_method: PaymentMethodDbEntity,
        payment_method_repository: PaymentMethodRepository,
    ):
        created_at = datetime.now(timezone.utc)
        insert_pgp_payment_method_input = InsertPgpPaymentMethodInput(
            id=uuid4(),
            payer_id=payment_method.payer_id,
            pgp_code=PgpCode.STRIPE,
            pgp_resource_id=str(uuid4()),
            payment_method_id=payment_method.id,
            created_at=created_at,
        )
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=insert_pgp_payment_method_input
        )
        assert pgp_payment_method is not None
        now = datetime.now(timezone.utc)
        input_set = DeletePgpPaymentMethodByIdSetInput(
            detached_at=now, deleted_at=now, updated_at=now
        )
        input_where = DeletePgpPaymentMethodByIdWhereInput(id=pgp_payment_method.id)
        deleted_pgp_payment_method = await payment_method_repository.delete_pgp_payment_method_by_id(
            input_set=input_set, input_where=input_where
        )
        assert deleted_pgp_payment_method is not None
        assert deleted_pgp_payment_method.deleted_at == now
        assert deleted_pgp_payment_method.detached_at == now
        assert deleted_pgp_payment_method.updated_at == now

    async def test_list_stripe_card_db_entities_by_stripe_customer_id(
        self,
        payment_method_repository: PaymentMethodRepository,
        payment_method: PaymentMethodDbEntity,
    ):
        created_at = datetime.now(timezone.utc)
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=InsertPgpPaymentMethodInput(
                id=uuid4(),
                payer_id=payment_method.payer_id,
                pgp_code=PgpCode.STRIPE,
                pgp_resource_id=str(uuid4()),
                payment_method_id=payment_method.id,
                created_at=created_at,
            )
        )
        stripe_card = await payment_method_repository.insert_stripe_card(
            sc_input=InsertStripeCardInput(
                stripe_id=pgp_payment_method.pgp_resource_id,
                fingerprint="",
                last4="",
                dynamic_last4="",
                exp_month="01",
                exp_year="2020",
                type="visa",
                active=True,
                external_stripe_customer_id=str(uuid4()),
            )
        )
        stripe_card_entities = await payment_method_repository.list_stripe_card_db_entities_by_stripe_customer_id(
            input=ListStripeCardDbEntitiesByStripeCustomerId(
                stripe_customer_id=stripe_card.external_stripe_customer_id
            )
        )
        assert len(stripe_card_entities) == 1
        assert stripe_card_entities[0] == stripe_card

    async def test_list_pgp_payment_method_entities_by_stripe_card_ids(
        self,
        payment_method_repository: PaymentMethodRepository,
        payment_method: PaymentMethodDbEntity,
    ):
        created_at = datetime.now(timezone.utc)
        pgp_payment_method = await payment_method_repository.insert_pgp_payment_method(
            pm_input=InsertPgpPaymentMethodInput(
                id=uuid4(),
                payer_id=payment_method.payer_id,
                pgp_code=PgpCode.STRIPE,
                pgp_resource_id=str(uuid4()),
                payment_method_id=payment_method.id,
                created_at=created_at,
            )
        )
        stripe_card = await payment_method_repository.insert_stripe_card(
            sc_input=InsertStripeCardInput(
                stripe_id=pgp_payment_method.pgp_resource_id,
                fingerprint="",
                last4="",
                dynamic_last4="",
                exp_month="01",
                exp_year="2020",
                type="visa",
                active=True,
                external_stripe_customer_id=str(uuid4()),
            )
        )
        pgp_payment_method_entities = await payment_method_repository.list_pgp_payment_method_entities_by_stripe_card_ids(
            input=ListPgpPaymentMethodByStripeCardId(
                stripe_id_list=[stripe_card.stripe_id]
            )
        )
        assert len(pgp_payment_method_entities) == 1
        assert pgp_payment_method_entities[0] == pgp_payment_method
