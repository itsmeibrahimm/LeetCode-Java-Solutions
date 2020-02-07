from uuid import uuid4

import pytest
from IPython.utils.tz import utcnow
from asynctest import MagicMock, CoroutineMock

from app.purchasecard.core.auth.models import (
    InternalCreateAuthResponse,
    InternalStoreInfo,
)
from app.purchasecard.core.auth.processor import AuthProcessor
from app.purchasecard.core.errors import (
    AuthRequestInconsistentStateError,
    AuthRequestNotFoundError,
)
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
        TEST_DASHER_ID = "TEST_DASHER_ID"
        TEST_STORE_ID = "123"
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
                external_purchasecard_user_token=TEST_DASHER_ID,
                store_id=TEST_STORE_ID,
                store_city="testcity",
                store_business_name="testbusinessname",
                current_state=AuthRequestStateName.ACTIVE_CREATED,
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
            store_id=TEST_STORE_ID,
            store_city="testcity",
            store_business_name="testbusinessname",
        )

        response: InternalCreateAuthResponse = await self.auth_processor.create_auth(
            subtotal=123,
            subtotal_tax=123,
            store_meta=test_store_info,
            delivery_id=TEST_DELIVERY_ID,
            shift_id=TEST_SHIFT_ID,
            external_user_token=TEST_DASHER_ID,
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
        UUID_THREE = uuid4()
        now = datetime.now(timezone.utc)

        auth_request = AuthRequest(
            id=UUID_ONE,
            created_at=now,
            updated_at=now + timedelta(hours=1),
            shift_id="3",
            delivery_id="4",
            external_purchasecard_user_token="5",
            store_id="2",
            store_city="Milpitas",
            store_business_name="In n Out",
            expire_sec=5,
            current_state=AuthRequestStateName.ACTIVE_CREATED,
        )

        auth_request_no_ttl = AuthRequest(
            id=UUID_ONE,
            created_at=now,
            updated_at=now,
            shift_id="3",
            delivery_id="4",
            external_purchasecard_user_token="5",
            store_id="2",
            store_city="Milpitas",
            store_business_name="In n Out",
            expire_sec=None,
            current_state=AuthRequestStateName.ACTIVE_CREATED,
        )

        self.auth_processor.authorization_master_repo.update_auth_request_ttl.return_value = (
            auth_request
        )

        self.auth_processor.authorization_master_repo.get_auth_request_by_delivery_shift_combination.return_value = (
            auth_request_no_ttl
        )

        self.auth_processor.authorization_master_repo.create_auth_request_state.return_value = (
            auth_request,
            AuthRequestState(
                id=UUID_THREE,
                auth_request_id=UUID_ONE,
                created_at=now,
                updated_at=now,
                state=AuthRequestStateName.ACTIVE_UPDATED,
                subtotal=10,
                subtotal_tax=20,
            ),
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
            store_id="2",
            store_city="Milpitas",
            store_business_name="In n Out",
            delivery_id="4",
            shift_id="3",
            ttl=None,
        )

        assert result_without_ttl.updated_at == now
        assert result_with_ttl.updated_at == now + timedelta(hours=1)

        assert result_with_ttl.state == AuthRequestStateName.ACTIVE_UPDATED
        assert result_without_ttl.state == AuthRequestStateName.ACTIVE_UPDATED

    async def test_close_auth(self):
        self.auth_processor.authorization_master_repo.get_auth_request_by_delivery_shift_combination = (
            CoroutineMock()
        )
        self.auth_processor.authorization_master_repo.get_auth_request_state_by_auth_id = (
            CoroutineMock()
        )
        self.auth_processor.authorization_master_repo.create_auth_request_state = (
            CoroutineMock()
        )

        UUID_ONE = uuid4()
        UUID_TWO = uuid4()
        UUID_THREE = uuid4()
        UUID_FOUR = uuid4()
        now = datetime.now(timezone.utc)

        auth_request = AuthRequest(
            id=UUID_ONE,
            created_at=now,
            updated_at=now + timedelta(hours=1),
            shift_id="4",
            delivery_id="5",
            external_purchasecard_user_token="6",
            store_id="3",
            store_city="Milpitas",
            store_business_name="Burger King",
            current_state=AuthRequestStateName.ACTIVE_CREATED,
            expire_sec=None,
        )

        self.auth_processor.authorization_master_repo.get_auth_request_by_delivery_shift_combination.return_value = (
            auth_request
        )

        self.auth_processor.authorization_master_repo.get_auth_request_state_by_auth_id.return_value = [
            AuthRequestState(
                id=UUID_THREE,
                auth_request_id=UUID_ONE,
                created_at=now + timedelta(microseconds=1),
                updated_at=now - timedelta(microseconds=1),
                state=AuthRequestStateName.ACTIVE_UPDATED,
                subtotal=10,
                subtotal_tax=20,
            ),
            AuthRequestState(
                id=UUID_TWO,
                auth_request_id=UUID_ONE,
                created_at=now + timedelta(microseconds=4),
                updated_at=now - timedelta(microseconds=4),
                state=AuthRequestStateName.ACTIVE_UPDATED,
                subtotal=2000,
                subtotal_tax=17,
            ),
            AuthRequestState(
                id=UUID_TWO,
                auth_request_id=UUID_ONE,
                created_at=now,
                updated_at=now,
                state=AuthRequestStateName.ACTIVE_UPDATED,
                subtotal=9,
                subtotal_tax=20,
            ),
        ]

        auth_request_updated = AuthRequest(
            id=UUID_ONE,
            created_at=now,
            updated_at=now + timedelta(hours=1),
            shift_id="4",
            delivery_id="5",
            external_purchasecard_user_token="6",
            store_id="3",
            store_city="Milpitas",
            store_business_name="Burger King",
            current_state=AuthRequestStateName.ACTIVE_CREATED,
            expire_sec=None,
        )

        self.auth_processor.authorization_master_repo.create_auth_request_state.return_value = (
            auth_request_updated,
            AuthRequestState(
                id=UUID_FOUR,
                auth_request_id=UUID_ONE,
                created_at=now + timedelta(hours=1),
                updated_at=now + timedelta(hours=1),
                state=AuthRequestStateName.CLOSED_MANUAL,
                subtotal=2000,
                subtotal_tax=17,
            ),
        )

        result_state: AuthRequestStateName = await self.auth_processor.close_auth(
            delivery_id="5", shift_id="4"
        )

        assert result_state == AuthRequestStateName.CLOSED_MANUAL
        assert (
            self.auth_processor.authorization_master_repo.create_auth_request_state.call_count
            == 1
        )
        assert (
            self.auth_processor.authorization_master_repo.create_auth_request_state.call_args[
                1
            ][
                "subtotal"
            ]
            == 2000
        )
        assert (
            self.auth_processor.authorization_master_repo.create_auth_request_state.call_args[
                1
            ][
                "subtotal_tax"
            ]
            == 17
        )

        self.auth_processor.authorization_master_repo.get_auth_request_state_by_auth_id.return_value = (
            []
        )

        with pytest.raises(AuthRequestInconsistentStateError):
            await self.auth_processor.close_auth(delivery_id="5", shift_id="4")

        self.auth_processor.authorization_master_repo.get_auth_request_by_delivery_shift_combination.return_value = (
            None
        )

        with pytest.raises(AuthRequestNotFoundError):
            await self.auth_processor.close_auth(delivery_id="5", shift_id="4")
