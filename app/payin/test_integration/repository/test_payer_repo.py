from datetime import datetime
from random import randint
from uuid import uuid4, UUID

import pytest
from pytz import timezone

from app.commons.types import CountryCode, PgpCode
from app.payin.core.payer.model import (
    DeletePayerSummary,
    DoorDashDomainRedact,
    RedactAction,
    StripeDomainRedact,
)
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.core.types import PayerReferenceIdType
from app.payin.models.paymentdb import (
    delete_payer_requests,
    delete_payer_requests_metadata,
)
from app.payin.repository.payer_repo import (
    PayerRepository,
    InsertPayerInput,
    GetPayerByIdInput,
    InsertPgpCustomerInput,
    GetPgpCustomerInput,
    UpdatePgpCustomerSetInput,
    UpdatePgpCustomerWhereInput,
    UpdatePayerSetInput,
    UpdatePayerWhereInput,
    GetConsumerIdByPayerIdInput,
    UpdateDeletePayerRequestWhereInput,
    UpdateDeletePayerRequestSetInput,
    GetDeletePayerRequestsByClientRequestIdInput,
    FindDeletePayerRequestByStatusInput,
    DeletePayerRequestDbEntity,
    GetPayerByLegacyDDStripeCustomerIdInput,
    GetPayerByPayerRefIdAndTypeInput,
    DeletePayerRequestMetadataDbEntity,
)


class TestPayerRepository:
    pytestmark = [pytest.mark.asyncio]

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
        self, delete_payer_summary, payer_repository: PayerRepository
    ):
        uuid = uuid4()
        yield await payer_repository.insert_delete_payer_request(
            DeletePayerRequestDbEntity(
                id=uuid,
                client_request_id=uuid,
                consumer_id=1,
                payer_id=None,
                status=DeletePayerRequestStatus.IN_PROGRESS.value,
                summary=delete_payer_summary.json(),
                retry_count=0,
                created_at=datetime.now(timezone("UTC")),
                updated_at=datetime.now(timezone("UTC")),
                acknowledged=False,
            )
        )
        await payer_repository.payment_database.master().execute(
            delete_payer_requests.table.delete().where(delete_payer_requests.id == uuid)
        )

    async def test_payer_timestamp_timezone(self, payer_repository: PayerRepository):
        created_at = datetime.now(timezone("Europe/Amsterdam"))
        insert_payer_input = InsertPayerInput(
            id=uuid4(),
            payer_reference_id_type=PayerReferenceIdType.DD_DRIVE_STORE_ID,
            country=CountryCode.US,
            created_at=created_at,
        )
        payer = await payer_repository.insert_payer(insert_payer_input)
        get_payer = await payer_repository.get_payer_by_id(
            GetPayerByIdInput(id=payer.id)
        )

        assert payer is not None
        assert get_payer is not None
        assert payer == get_payer
        assert get_payer.created_at is not None
        assert created_at.timestamp() == get_payer.created_at.timestamp()

    async def test_get_payer_entity(self, payer_repository: PayerRepository):
        payer_id = uuid4()
        legacy_dd_stripe_customer_id = 1234
        payer_reference_id = "123"

        insert_payer_input = InsertPayerInput(
            id=payer_id,
            payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
            payer_reference_id="123",
            country=CountryCode.US,
            primary_pgp_code=PgpCode.STRIPE,
            primary_pgp_payer_resource_id="cus_123456",
            primary_pgp_payer_id=uuid4(),
            legacy_dd_stripe_customer_id=legacy_dd_stripe_customer_id,
        )
        await payer_repository.insert_payer(insert_payer_input)

        payer_entity_1 = await payer_repository.get_payer_by_id(
            request=GetPayerByIdInput(id=payer_id)
        )

        payer_entity_2 = await payer_repository.get_payer_by_legacy_dd_stripe_customer_id(
            request=GetPayerByLegacyDDStripeCustomerIdInput(
                legacy_dd_stripe_customer_id=legacy_dd_stripe_customer_id
            )
        )

        payer_entity_3 = await payer_repository.get_payer_by_reference_id_and_type(
            input=GetPayerByPayerRefIdAndTypeInput(
                payer_reference_id=payer_reference_id,
                payer_reference_id_type=PayerReferenceIdType.DD_CONSUMER_ID,
            )
        )

        assert payer_entity_1 == payer_entity_2 == payer_entity_3

    async def test_pgp_customer_crud(self, payer_repository: PayerRepository):
        # TODO: [PAYIN-37] don't need to create payer after we remove the foreign key constraint
        insert_payer_input = InsertPayerInput(
            id=uuid4(),
            payer_reference_id_type=PayerReferenceIdType.DD_DRIVE_STORE_ID,
            country=CountryCode.US,
        )
        payer = await payer_repository.insert_payer(insert_payer_input)

        # test insert and get
        insert_pgp_customer_input = InsertPgpCustomerInput(
            id=uuid4(),
            payer_id=payer.id,
            pgp_resource_id="fake_stripe_customer_id",
            country="US",
            is_primary=True,
            pgp_code="stripe",
            balance=100,
            default_payment_method_id="fake_default_payment_method_id",
            created_at=datetime.utcnow(),
        )
        pgp_customer = await payer_repository.insert_pgp_customer(
            insert_pgp_customer_input
        )
        assert pgp_customer.country is not None
        assert pgp_customer.is_primary is not None
        assert pgp_customer.balance is not None
        assert pgp_customer.default_payment_method_id is not None

        get_pgp_customer = await payer_repository.get_pgp_customer(
            GetPgpCustomerInput(payer_id=payer.id)
        )
        assert pgp_customer == get_pgp_customer

        # test update and get
        updated_at = datetime.utcnow()
        updated_default_payment_method_id = "new_fake_default_payment_method_id"
        updated_pgp_customer = await payer_repository.update_pgp_customer(
            request_set=UpdatePgpCustomerSetInput(
                updated_at=updated_at,
                default_payment_method_id=updated_default_payment_method_id,
            ),
            request_where=UpdatePgpCustomerWhereInput(id=pgp_customer.id),
        )
        assert (
            updated_pgp_customer.default_payment_method_id
            == updated_default_payment_method_id
        )

        get_pgp_customer = await payer_repository.get_pgp_customer(
            GetPgpCustomerInput(payer_id=payer.id)
        )
        assert updated_pgp_customer == get_pgp_customer

    async def test_payer_default_payment_method(
        self, payer_repository: PayerRepository
    ):
        payer_id: UUID = uuid4()
        default_payment_method_id: UUID = uuid4()
        legacy_default_dd_stripe_card_id: int = 1
        insert_payer_input = InsertPayerInput(
            id=payer_id,
            payer_reference_id_type=PayerReferenceIdType.DD_DRIVE_STORE_ID,
            country=CountryCode.US,
            default_payment_method_id=default_payment_method_id,
            legacy_default_dd_stripe_card_id=legacy_default_dd_stripe_card_id,
        )
        payer = await payer_repository.insert_payer(request=insert_payer_input)
        assert (
            payer.legacy_default_dd_stripe_card_id == legacy_default_dd_stripe_card_id
        )
        assert payer.default_payment_method_id == default_payment_method_id

        update_payer = await payer_repository.update_payer_by_id(
            request_set=UpdatePayerSetInput(
                default_payment_method_id=None,
                legacy_default_dd_stripe_card_id=None,
                updated_at=datetime.now(timezone("UTC")),
            ),
            request_where=UpdatePayerWhereInput(id=payer_id),
        )
        assert update_payer.legacy_default_dd_stripe_card_id is None
        assert update_payer.default_payment_method_id is None

        # reset default payment method
        new_default_payment_method_id: UUID = uuid4()
        new_legacy_default_dd_stripe_card_id: int = 2
        update_payer = await payer_repository.update_payer_by_id(
            request_set=UpdatePayerSetInput(
                default_payment_method_id=new_default_payment_method_id,
                legacy_default_dd_stripe_card_id=new_legacy_default_dd_stripe_card_id,
                updated_at=datetime.now(timezone("UTC")),
            ),
            request_where=UpdatePayerWhereInput(id=payer_id),
        )
        assert (
            update_payer.legacy_default_dd_stripe_card_id
            == new_legacy_default_dd_stripe_card_id
        )
        assert update_payer.default_payment_method_id == new_default_payment_method_id

        # partial update
        new_legacy_default_dd_stripe_card_id = 3
        update_payer = await payer_repository.update_payer_by_id(
            request_set=UpdatePayerSetInput(
                legacy_default_dd_stripe_card_id=new_legacy_default_dd_stripe_card_id,
                updated_at=datetime.now(timezone("UTC")),
            ),
            request_where=UpdatePayerWhereInput(id=payer_id),
        )
        assert (
            update_payer.legacy_default_dd_stripe_card_id
            == new_legacy_default_dd_stripe_card_id
        )
        assert update_payer.default_payment_method_id == new_default_payment_method_id

    async def test_get_consumer_id_by_payer_id(self, payer_repository: PayerRepository):
        payer_id: UUID = uuid4()
        default_payment_method_id: UUID = uuid4()
        legacy_default_dd_stripe_card_id: int = 1
        insert_payer_input = InsertPayerInput(
            id=payer_id,
            country=CountryCode.US,
            default_payment_method_id=default_payment_method_id,
            legacy_default_dd_stripe_card_id=legacy_default_dd_stripe_card_id,
            payer_reference_id=randint(1, 1000),
            payer_reference_id_type=PayerReferenceIdType.DD_DRIVE_STORE_ID,
        )
        payer = await payer_repository.insert_payer(request=insert_payer_input)
        assert payer
        consumer_id = await payer_repository.get_consumer_id_by_payer_id(
            input=GetConsumerIdByPayerIdInput(payer_id=str(payer_id))
        )
        assert consumer_id
        assert consumer_id == insert_payer_input.payer_reference_id

    @pytest.mark.asyncio
    async def test_insert_delete_payer_request_metadata(
        self, payer_repository: PayerRepository
    ):
        uuid = uuid4()
        now = datetime.now(timezone("UTC"))
        result = await payer_repository.insert_delete_payer_request_metadata(
            DeletePayerRequestMetadataDbEntity(
                id=uuid,
                client_request_id=uuid,
                consumer_id=123,
                country_code=CountryCode.US,
                email="john.doe@doordash.com",
                status=DeletePayerRequestStatus.IN_PROGRESS.value,
                created_at=now,
                updated_at=now,
            )
        )

        await payer_repository.payment_database.master().execute(
            delete_payer_requests_metadata.table.delete()
        )

        expected_delete_payer_request = DeletePayerRequestMetadataDbEntity(
            id=uuid,
            client_request_id=uuid,
            consumer_id=123,
            country_code=CountryCode.US,
            email="john.doe@doordash.com",
            status=DeletePayerRequestStatus.IN_PROGRESS.value,
            created_at=now,
            updated_at=now,
        )

        assert result == expected_delete_payer_request

    @pytest.mark.asyncio
    async def test_insert_delete_payer_request(
        self, delete_payer_summary, payer_repository: PayerRepository
    ):
        uuid = uuid4()
        now = datetime.now(timezone("UTC"))
        result = await payer_repository.insert_delete_payer_request(
            DeletePayerRequestDbEntity(
                id=uuid,
                client_request_id=uuid,
                consumer_id=123,
                payer_id=None,
                status=DeletePayerRequestStatus.IN_PROGRESS.value,
                summary=delete_payer_summary.json(),
                retry_count=0,
                created_at=now,
                updated_at=now,
                acknowledged=False,
            )
        )

        await payer_repository.payment_database.master().execute(
            delete_payer_requests.table.delete()
        )

        expected_delete_payer_request = DeletePayerRequestDbEntity(
            id=uuid,
            client_request_id=uuid,
            consumer_id=123,
            payer_id=None,
            status=DeletePayerRequestStatus.IN_PROGRESS.value,
            summary=delete_payer_summary.json(),
            retry_count=0,
            created_at=now,
            updated_at=now,
            acknowledged=False,
        )

        assert result == expected_delete_payer_request

    @pytest.mark.asyncio
    async def test_get_delete_payer_requests_by_client_request_id(
        self, payer_repository: PayerRepository, delete_payer_request
    ):
        results = await payer_repository.get_delete_payer_requests_by_client_request_id(
            get_delete_payer_requests_by_client_request_id_input=GetDeletePayerRequestsByClientRequestIdInput(
                client_request_id=delete_payer_request.client_request_id
            )
        )

        expected_delete_payer_request = DeletePayerRequestDbEntity(
            id=delete_payer_request.id,
            client_request_id=delete_payer_request.client_request_id,
            consumer_id=delete_payer_request.consumer_id,
            payer_id=delete_payer_request.payer_id,
            status=delete_payer_request.status,
            summary=delete_payer_request.summary,
            retry_count=delete_payer_request.retry_count,
            created_at=delete_payer_request.created_at,
            updated_at=delete_payer_request.updated_at,
            acknowledged=delete_payer_request.acknowledged,
        )

        assert results
        assert len(results) == 1
        assert results[0] == expected_delete_payer_request

    @pytest.mark.asyncio
    async def test_find_delete_payer_requests_by_status(
        self, payer_repository: PayerRepository, delete_payer_request
    ):
        results = await payer_repository.find_delete_payer_requests_by_status(
            find_delete_payer_request_by_status_input=FindDeletePayerRequestByStatusInput(
                status=DeletePayerRequestStatus.IN_PROGRESS
            )
        )

        assert results
        assert len(results) > 0
        for request in results:
            assert request.status == DeletePayerRequestStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_update_delete_payer_request(
        self, payer_repository, delete_payer_request
    ):
        now = datetime.now(timezone("UTC"))
        result = await payer_repository.update_delete_payer_request(
            update_delete_payer_request_where_input=UpdateDeletePayerRequestWhereInput(
                client_request_id=delete_payer_request.client_request_id
            ),
            update_delete_payer_request_set_input=UpdateDeletePayerRequestSetInput(
                status=DeletePayerRequestStatus.SUCCEEDED.value,
                summary=delete_payer_request.summary,
                retry_count=0,
                updated_at=now,
                acknowledged=True,
            ),
        )

        expected_delete_payer_request = DeletePayerRequestDbEntity(
            id=delete_payer_request.id,
            client_request_id=delete_payer_request.client_request_id,
            consumer_id=delete_payer_request.consumer_id,
            payer_id=delete_payer_request.payer_id,
            status=DeletePayerRequestStatus.SUCCEEDED.value,
            summary=delete_payer_request.summary,
            retry_count=0,
            created_at=delete_payer_request.created_at,
            updated_at=now,
            acknowledged=True,
        )

        assert result == expected_delete_payer_request
