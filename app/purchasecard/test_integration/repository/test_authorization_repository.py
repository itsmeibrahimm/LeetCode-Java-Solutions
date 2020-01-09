import uuid
from random import randint

import pytest
from typing_extensions import TypedDict

from app.commons.database.infra import DB
from app.purchasecard.repository.authorization_repository import (
    AuthorizationMasterRepository,
    AuthorizationReplicaRepository,
)
from app.purchasecard.repository.base import NonValidReplicaOperation


class SimpleIntegerIdContainer:
    def __init__(self, num_ids):
        self._ids = [172] * num_ids
        self._num_ids = num_ids

    def increment_random_id(self):
        idx = randint(0, self._num_ids - 1)
        self._ids[idx] += 1
        return self._ids


@pytest.fixture(scope="module")
def unique_shift_delivery_store_id_generator():
    return SimpleIntegerIdContainer(3)


@pytest.mark.asyncio
class TestAuthorizationtMasterRepository:

    TEST_MID_ID = "test mid"
    TEST_MID_ID_2 = "test mid 2"
    TEST_MID_ID_3 = "test mid 3"
    TEST_STORE_ID = 123
    TEST_MNAME = "test name"

    @pytest.fixture
    def authorization_master_repo(
        self, purchasecard_paymentdb: DB
    ) -> AuthorizationMasterRepository:
        return AuthorizationMasterRepository(database=purchasecard_paymentdb)

    @pytest.fixture
    def authorization_replica_repo(
        self, purchasecard_paymentdb: DB
    ) -> AuthorizationReplicaRepository:
        return AuthorizationReplicaRepository(database=purchasecard_paymentdb)

    async def test_create_authorization(
        self,
        authorization_master_repo,
        authorization_replica_repo,
        unique_shift_delivery_store_id_generator: SimpleIntegerIdContainer,
    ):
        ids = unique_shift_delivery_store_id_generator.increment_random_id()

        class AnnoyingMyPyDict(TypedDict):
            auth_id: uuid.UUID
            state_id: uuid.UUID
            shift_id: str
            delivery_id: str
            store_id: str
            store_city: str
            store_business_name: str
            subtotal: int
            subtotal_tax: int
            dasher_id: str

        fake_auth_request: AnnoyingMyPyDict = {
            "auth_id": uuid.uuid4(),
            "state_id": uuid.uuid4(),
            "shift_id": str(ids[0]),
            "delivery_id": str(ids[1]),
            "store_id": str(ids[2]),
            "store_city": "Mountain View",
            "store_business_name": "jazzy jasmine tea",
            "subtotal": 3,
            "subtotal_tax": 5,
            "dasher_id": "7",
        }
        auth, auth_state = await authorization_master_repo.create_authorization(
            **fake_auth_request
        )
        assert auth.id == fake_auth_request["auth_id"]
        assert auth_state.id == fake_auth_request["state_id"]

        with pytest.raises(NonValidReplicaOperation):
            await authorization_replica_repo.create_authorization(**fake_auth_request)

    async def test_gets(
        self,
        authorization_master_repo,
        authorization_replica_repo,
        unique_shift_delivery_store_id_generator: SimpleIntegerIdContainer,
    ):
        ids = unique_shift_delivery_store_id_generator.increment_random_id()

        class AnnoyingMyPyDict(TypedDict):
            auth_id: uuid.UUID
            state_id: uuid.UUID
            shift_id: str
            delivery_id: str
            store_id: str
            store_city: str
            store_business_name: str
            subtotal: int
            subtotal_tax: int
            dasher_id: str

        fake_auth_request: AnnoyingMyPyDict = {
            "auth_id": uuid.uuid4(),
            "state_id": uuid.uuid4(),
            "shift_id": str(ids[0]),
            "delivery_id": str(ids[1]),
            "store_id": str(ids[2]),
            "store_city": "Mountain View",
            "store_business_name": "jazzy jasmine tea",
            "subtotal": 3,
            "subtotal_tax": 5,
            "dasher_id": "7",
        }
        auth, auth_state = await authorization_master_repo.create_authorization(
            **fake_auth_request
        )

        get_auth_master_result = await authorization_master_repo.get_auth_request(
            fake_auth_request["auth_id"]
        )

        get_auth_replica_result = await authorization_replica_repo.get_auth_request(
            fake_auth_request["auth_id"]
        )

        get_auth_state_master_result = await authorization_master_repo.get_auth_request_state(
            fake_auth_request["state_id"]
        )

        get_auth_state_replica_result = await authorization_replica_repo.get_auth_request_state(
            fake_auth_request["state_id"]
        )

        get_auth_state_by_auth_id_master_result = await authorization_master_repo.get_auth_request_state_by_auth_id(
            fake_auth_request["auth_id"]
        )

        get_auth_state_by_auth_id_replica_result = await authorization_replica_repo.get_auth_request_state_by_auth_id(
            fake_auth_request["auth_id"]
        )

        assert auth.id == get_auth_master_result.id
        assert auth.id == get_auth_replica_result.id

        assert auth_state.id == get_auth_state_master_result.id
        assert auth_state.id == get_auth_state_replica_result.id

        assert auth_state.id == get_auth_state_by_auth_id_master_result.id
        assert auth_state.id == get_auth_state_by_auth_id_replica_result.id

        non_existent_id_result = await authorization_replica_repo.get_auth_request(
            uuid.uuid4()
        )

        assert non_existent_id_result == None
