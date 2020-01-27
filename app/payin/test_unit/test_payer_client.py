from datetime import datetime, timezone
from typing import List
from uuid import uuid4

import pytest
from asynctest import MagicMock
from stripe.error import StripeError

from app.commons.core.errors import DBOperationError, DBIntegrityUniqueViolationError
from app.commons.providers.stripe.stripe_models import (
    StripeDeleteCustomerResponse,
    Customer,
    InvoiceSettings,
    Customers,
)
from app.commons.types import CountryCode
from app.payin.core.exceptions import PayerDeleteError, PayinErrorCode
from app.payin.core.payer.model import (
    DeletePayerSummary,
    RedactAction,
    DoorDashDomainRedact,
    StripeDomainRedact,
)
from app.payin.core.payer.payer_client import PayerClient
from app.payin.core.payer.types import DeletePayerRequestStatus
from app.payin.repository.payer_repo import (
    DeletePayerRequestDbEntity,
    DeletePayerRequestMetadataDbEntity,
)
from app.payin.tests.utils import FunctionMock, generate_delete_payer_request


class TestPayerClient:
    """
    Test internal facing functions exposed by app/payin/core/payer/payer_client.py.
    """

    @pytest.fixture
    def payer_client(self):
        payer_client = PayerClient(
            app_ctxt=MagicMock(),
            log=MagicMock(),
            payer_repo=MagicMock(),
            stripe_async_client=MagicMock(),
        )
        return payer_client

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

    @pytest.mark.asyncio
    async def test_pgp_get_customers(self, payer_client):
        customers_list: List[Customer] = [
            Customer(
                id="cus_1234567",
                object="customer",
                created=datetime.now(timezone.utc),
                currency="USD",
                invoice_settings=InvoiceSettings(default_payment_method=""),
                default_source="",
                description="",
                email="john.doe@gmail.com",
            )
        ]
        payer_client.stripe_async_client.list_customers = FunctionMock(
            return_value=Customers(
                object="list", url="/v1/customers", has_more=False, data=customers_list
            )
        )
        customers: List[Customer] = await payer_client.pgp_get_customers(
            email="john.doe@gmail.com", country_code=CountryCode.US
        )
        assert customers == customers_list

    @pytest.mark.asyncio
    async def test_pgp_get_customers_multiple_pgp_calls(self, payer_client):
        customers_list: List[Customer] = []
        for i in range(200):
            customer = Customer(
                id=f"cus_{i}",
                object="customer",
                created=datetime.now(timezone.utc),
                currency="USD",
                invoice_settings=InvoiceSettings(default_payment_method=""),
                default_source="",
                description=f"customer {i}",
                email="john.doe@gmail.com",
            )
            customers_list.append(customer)

        payer_client.stripe_async_client.list_customers = FunctionMock(
            side_effect=[
                Customers(
                    object="list",
                    url="/v1/customers",
                    has_more=True,
                    data=customers_list[0:100],
                ),
                Customers(
                    object="list",
                    url="/v1/customers",
                    has_more=False,
                    data=customers_list[100:200],
                ),
            ]
        )
        customers: List[Customer] = await payer_client.pgp_get_customers(
            email="john.doe@gmail.com", country_code=CountryCode.US
        )
        assert customers == customers_list

    @pytest.mark.asyncio
    async def test_pgp_delete_customer(self, payer_client):
        payer_client.stripe_async_client.delete_customer = FunctionMock(
            return_value=StripeDeleteCustomerResponse(
                id="cus_1234567", object="customer", deleted=True
            )
        )
        stripe_delete_customer_response = await payer_client.pgp_delete_customer(
            CountryCode.US, "cus_1234567"
        )
        assert stripe_delete_customer_response.deleted is True

    @pytest.mark.asyncio
    async def test_pgp_delete_customer_errors(self, payer_client):
        payer_client.stripe_async_client.delete_customer = FunctionMock(
            side_effect=StripeError()
        )
        with pytest.raises(PayerDeleteError) as e:
            await payer_client.pgp_delete_customer(CountryCode.US, "cus_1234567")
        assert e.value.error_code == PayinErrorCode.PAYER_DELETE_STRIPE_ERROR

    @pytest.mark.asyncio
    async def test_pgp_delete_customer_errors_not_found(self, payer_client):
        payer_client.stripe_async_client.delete_customer = FunctionMock(
            side_effect=StripeError(
                json_body={
                    "error": {
                        "code": "resource_missing",
                        "doc_url": "https://stripe.com/docs/error-codes/resource-missing",
                        "message": "No such customer: cus_1234567",
                        "param": "id",
                        "type": "invalid_request_error",
                    }
                }
            )
        )
        with pytest.raises(PayerDeleteError) as e:
            await payer_client.pgp_delete_customer(CountryCode.US, "cus_1234567")
        assert e.value.error_code == PayinErrorCode.PAYER_DELETE_STRIPE_ERROR_NOT_FOUND

    @pytest.mark.asyncio
    async def test_insert_delete_payer_request_metadata(self, payer_client):
        delete_payer_request_metadata: DeletePayerRequestMetadataDbEntity = DeletePayerRequestMetadataDbEntity(
            id=uuid4(),
            client_request_id=uuid4(),
            consumer_id=123,
            country_code=CountryCode.US,
            email="john.doe@doordash.com",
            status=DeletePayerRequestStatus.IN_PROGRESS,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        payer_client.payer_repo.insert_delete_payer_request_metadata = FunctionMock(
            return_value=delete_payer_request_metadata
        )
        inserted_delete_payer_request_metadata = await payer_client.insert_delete_payer_request_metadata(
            client_request_id=delete_payer_request_metadata.client_request_id,
            consumer_id=delete_payer_request_metadata.consumer_id,
            country_code=delete_payer_request_metadata.country_code,
            email=delete_payer_request_metadata.email,
        )
        assert inserted_delete_payer_request_metadata == delete_payer_request_metadata

    @pytest.mark.asyncio
    async def test_insert_delete_payer_request_metadata_errors(self, payer_client):
        payer_client.payer_repo.insert_delete_payer_request_metadata = FunctionMock(
            side_effect=DBIntegrityUniqueViolationError()
        )
        with pytest.raises(PayerDeleteError) as e:
            await payer_client.insert_delete_payer_request_metadata(
                client_request_id=uuid4(),
                consumer_id=123,
                country_code=CountryCode.US,
                email="john.doe@doordash.com",
            )
        assert (
            e.value.error_code
            == PayinErrorCode.DELETE_PAYER_REQUEST_METADATA_INSERT_DB_ERROR
        )

    @pytest.mark.asyncio
    async def test_insert_delete_payer_request(
        self, payer_client, delete_payer_summary
    ):
        delete_payer_request = generate_delete_payer_request(
            summary=delete_payer_summary.json()
        )
        payer_client.payer_repo.insert_delete_payer_request = FunctionMock(
            return_value=delete_payer_request
        )
        inserted_delete_payer_request = await payer_client.insert_delete_payer_request(
            client_request_id=delete_payer_request.client_request_id,
            consumer_id=delete_payer_request.consumer_id,
        )
        assert inserted_delete_payer_request
        assert inserted_delete_payer_request.id == delete_payer_request.id

    @pytest.mark.asyncio
    async def test_insert_delete_payer_request_errors(
        self, payer_client, delete_payer_summary
    ):
        delete_payer_request = generate_delete_payer_request(
            summary=delete_payer_summary.json()
        )
        payer_client.payer_repo.insert_delete_payer_request = FunctionMock(
            side_effect=DBOperationError(error_message="")
        )
        with pytest.raises(PayerDeleteError) as e:
            await payer_client.insert_delete_payer_request(
                client_request_id=delete_payer_request.client_request_id,
                consumer_id=delete_payer_request.consumer_id,
            )
        assert e.value.error_code == PayinErrorCode.DELETE_PAYER_REQUEST_INSERT_DB_ERROR

    @pytest.mark.asyncio
    async def test_update_delete_payer_request(
        self, payer_client, delete_payer_summary
    ):
        delete_payer_request = generate_delete_payer_request(
            status=DeletePayerRequestStatus.SUCCEEDED,
            summary=delete_payer_summary.json(),
            retry_count=0,
            acknowledged=True,
        )
        payer_client.payer_repo.update_delete_payer_request = FunctionMock(
            return_value=delete_payer_request
        )
        updated_delete_payer_request = await payer_client.update_delete_payer_request(
            client_request_id=delete_payer_request.client_request_id,
            status=DeletePayerRequestStatus.SUCCEEDED,
            summary=delete_payer_summary.json(),
            retry_count=0,
            acknowledged=True,
        )
        assert updated_delete_payer_request
        assert updated_delete_payer_request.status == DeletePayerRequestStatus.SUCCEEDED
        assert updated_delete_payer_request.acknowledged

    @pytest.mark.asyncio
    async def test_update_delete_payer_request_errors(
        self, payer_client, delete_payer_summary
    ):
        delete_payer_request = generate_delete_payer_request(
            status=DeletePayerRequestStatus.SUCCEEDED,
            summary=delete_payer_summary.json(),
            retry_count=0,
            acknowledged=True,
        )
        payer_client.payer_repo.update_delete_payer_request = FunctionMock(
            side_effect=DBOperationError(error_message="")
        )
        with pytest.raises(PayerDeleteError) as e:
            await payer_client.update_delete_payer_request(
                client_request_id=delete_payer_request.client_request_id,
                status=DeletePayerRequestStatus.SUCCEEDED,
                summary=delete_payer_summary.json(),
                retry_count=0,
                acknowledged=True,
            )
        assert e.value.error_code == PayinErrorCode.DELETE_PAYER_REQUEST_UPDATE_DB_ERROR

    @pytest.mark.asyncio
    async def test_get_delete_payer_requests_by_client_request_id(
        self, payer_client, delete_payer_summary
    ):
        delete_payer_request = generate_delete_payer_request(
            summary=delete_payer_summary.json()
        )
        delete_payer_requests = [delete_payer_request]
        payer_client.payer_repo.get_delete_payer_requests_by_client_request_id = FunctionMock(
            return_value=delete_payer_requests
        )
        filtered_delete_payer_requests: List[
            DeletePayerRequestDbEntity
        ] = await payer_client.get_delete_payer_requests_by_client_request_id(
            client_request_id=delete_payer_request.client_request_id
        )
        assert len(filtered_delete_payer_requests) == 1
        assert filtered_delete_payer_requests[0].id == delete_payer_request.id
