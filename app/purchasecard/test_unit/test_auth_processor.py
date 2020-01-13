from uuid import uuid4

import pytest
from IPython.utils.tz import utcnow
from asynctest import MagicMock, CoroutineMock

from app.purchasecard.core.auth.models import (
    InternalCreateAuthResponse,
    InternalStoreInfo,
)
from app.purchasecard.core.auth.processor import AuthProcessor
from app.purchasecard.models.paymentdb.auth_request import AuthRequest
from app.purchasecard.models.paymentdb.auth_request_state import (
    AuthRequestState,
    AuthRequestStateName,
)
from datetime import datetime, timezone, timedelta


class TestAuthProcessor:
    pytestmark = [pytest.mark.asyncio]

    @pytest.fixture(autouse=True)
    def setup(
        self,
        fake_marqeta_client,
        mock_authorization_master_repo,
        mock_authorization_replica_repo,
    ):
        self.auth_processor = AuthProcessor(
            logger=MagicMock(),
            marqeta_client=fake_marqeta_client,
            authorization_master_repo=mock_authorization_master_repo,
            authorization_replica_repo=mock_authorization_replica_repo,
        )

    @pytest.fixture
    def fake_marqeta_client(self):
        mock_marqeta_client = MagicMock()
        return mock_marqeta_client

    async def test_create(self):
        """
        mock DB calls
        """
        TEST_AUTH_REQUEST_ID = uuid4()
        TEST_AUTH_REQUEST_STATE_ID = uuid4()
        TEST_SHIFT_ID = "TEST_SHIFT_ID"
        TEST_DELIVERY_ID = "TEST_DELIVERY_ID"
        self.auth_processor.authorization_master_repo.create_authorization = (
            CoroutineMock()
        )
        self.auth_processor.authorization_master_repo.create_authorization.return_value = (
            AuthRequest(
                id=TEST_AUTH_REQUEST_ID,
                created_at=utcnow(),
                updated_at=utcnow(),
                shift_id=TEST_SHIFT_ID,
                delivery_id=TEST_DELIVERY_ID,
                store_id="123",
                store_city="testcity",
                store_business_name="testbusinessname",
            ),
            AuthRequestState(
                id=TEST_AUTH_REQUEST_STATE_ID,
                auth_request_id=TEST_AUTH_REQUEST_ID,
                created_at=utcnow(),
                updated_at=utcnow(),
                state=AuthRequestStateName.ACTIVE_CREATED,
                subtotal=123,
                subtotal_tax=123,
            ),
        )

        test_store_info = InternalStoreInfo(
            store_id="123",
            store_city="testcity",
            store_business_name="testbusinessname",
        )

        response: InternalCreateAuthResponse = await self.auth_processor.create_auth(
            subtotal=123,
            subtotal_tax=123,
            store_meta=test_store_info,
            delivery_id=TEST_DELIVERY_ID,
            delivery_requires_purchase_card=True,
            shift_id=TEST_SHIFT_ID,
            ttl=None,
        )

        assert response
        assert response.delivery_id == TEST_DELIVERY_ID

    async def test_updates_auth(self):
        self.auth_processor.authorization_master_repo.update_auth_request_ttl = (
            CoroutineMock()
        )
        self.auth_processor.authorization_master_repo.get_auth_request_by_delivery_shift_combination = (
            CoroutineMock()
        )
        self.auth_processor.authorization_master_repo.create_auth_request_state = (
            CoroutineMock()
        )

        UUID_ONE = uuid4()
        UUID_TWO = uuid4()
        UUID_THREE = uuid4()
        now = datetime.now(timezone.utc)
        self.auth_processor.authorization_master_repo.update_auth_request_ttl.return_value = AuthRequest(
            id=UUID_ONE,
            created_at=now,
            updated_at=now,
            shift_id="3",
            delivery_id="4",
            dasher_id=None,
            store_id="2",
            store_city="Milpitas",
            store_business_name="In n Out",
            expire_sec=5,
        )

        self.auth_processor.authorization_master_repo.get_auth_request_by_delivery_shift_combination.return_value = AuthRequest(
            id=UUID_TWO,
            created_at=now,
            updated_at=now + timedelta(hours=1),
            shift_id="4",
            delivery_id="5",
            dasher_id=None,
            store_id="3",
            store_city="Milpitas",
            store_business_name="Burger King",
            expire_sec=None,
        )

        self.auth_processor.authorization_master_repo.create_auth_request_state.return_value = AuthRequestState(
            id=UUID_THREE,
            auth_request_id=UUID_ONE,
            created_at=now,
            updated_at=now,
            state=AuthRequestStateName.ACTIVE_UPDATED,
            subtotal=10,
            subtotal_tax=20,
        )

        result_with_ttl = await self.auth_processor.update_auth(
            subtotal=10,
            subtotal_tax=20,
            store_id="2",
            store_city="Milpitas",
            store_business_name="In n Out",
            delivery_id="4",
            shift_id="3",
            ttl=5,
        )

        result_without_ttl = await self.auth_processor.update_auth(
            subtotal=10,
            subtotal_tax=20,
            store_id="3",
            store_city="Milpitas",
            store_business_name="Burger King",
            delivery_id="5",
            shift_id="4",
            ttl=None,
        )

        assert result_with_ttl.updated_at == now
        assert result_without_ttl.updated_at == now + timedelta(hours=1)

        assert result_with_ttl.state == AuthRequestStateName.ACTIVE_UPDATED
        assert result_without_ttl.state == AuthRequestStateName.ACTIVE_UPDATED
