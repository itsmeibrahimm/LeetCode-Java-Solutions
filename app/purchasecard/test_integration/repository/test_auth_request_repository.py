import uuid
from random import randint

import pytest
from typing_extensions import TypedDict

from app.commons.database.infra import DB
from app.purchasecard.repository.auth_request_repository import (
    AuthRequestMasterRepository,
    AuthRequestRepositoryInterface,
    AuthRequestReplicaRepository,
)
from app.purchasecard.repository.base import NonValidReplicaOperation


class SimpleIntegerIdContainer:
    def __init__(self, num_ids):
        self._ids = [170] * num_ids
        self._num_ids = num_ids

    def increment_random_id(self):
        idx = randint(0, self._num_ids - 1)
        self._ids[idx] += 1
        return self._ids


@pytest.fixture(scope="module")
def unique_shift_delivery_store_id_generator():
    return SimpleIntegerIdContainer(3)


@pytest.mark.asyncio
class TestAuthRequestMasterRepository:

    TEST_MID_ID = "test mid"
    TEST_MID_ID_2 = "test mid 2"
    TEST_MID_ID_3 = "test mid 3"
    TEST_STORE_ID = 123
    TEST_MNAME = "test name"

    @pytest.fixture
    def auth_request_master_repo(
        self, purchasecard_paymentdb: DB
    ) -> AuthRequestMasterRepository:
        return AuthRequestMasterRepository(database=purchasecard_paymentdb)

    @pytest.fixture
    def auth_request_replica_repo(
        self, purchasecard_paymentdb: DB
    ) -> AuthRequestReplicaRepository:
        return AuthRequestReplicaRepository(database=purchasecard_paymentdb)

    async def test_insert(
        self,
        auth_request_master_repo: AuthRequestRepositoryInterface,
        auth_request_replica_repo: AuthRequestRepositoryInterface,
        unique_shift_delivery_store_id_generator: SimpleIntegerIdContainer,
    ):
        ids = unique_shift_delivery_store_id_generator.increment_random_id()

        class AnnoyingMyPyDict(TypedDict):
            id: uuid.UUID
            shift_id: str
            delivery_id: str
            store_id: str
            store_city: str
            store_business_name: str
            dasher_id: str

        fake_auth_request: AnnoyingMyPyDict = {
            "id": uuid.uuid4(),
            "shift_id": str(ids[0]),
            "delivery_id": str(ids[1]),
            "store_id": str(ids[2]),
            "store_city": "Mountain View",
            "store_business_name": "jazzy jasmine tea",
            "dasher_id": "7",
        }
        result = await auth_request_master_repo.insert(**fake_auth_request)
        assert result.id == fake_auth_request["id"]

        with pytest.raises(NonValidReplicaOperation):
            await auth_request_replica_repo.insert(**fake_auth_request)

    async def test_get(
        self,
        auth_request_master_repo: AuthRequestRepositoryInterface,
        auth_request_replica_repo: AuthRequestRepositoryInterface,
        unique_shift_delivery_store_id_generator: SimpleIntegerIdContainer,
    ):
        ids = unique_shift_delivery_store_id_generator.increment_random_id()

        class AnnoyingMyPyDict(TypedDict):
            id: uuid.UUID
            shift_id: str
            delivery_id: str
            store_id: str
            store_city: str
            store_business_name: str
            dasher_id: str

        fake_auth_request: AnnoyingMyPyDict = {
            "id": uuid.uuid4(),
            "shift_id": str(ids[0]),
            "delivery_id": str(ids[1]),
            "store_id": str(ids[2]),
            "store_city": "Mountain View",
            "store_business_name": "jazzy jasmine tea",
            "dasher_id": "7",
        }

        insert_result = await auth_request_master_repo.insert(**fake_auth_request)

        get_master_result = await auth_request_master_repo.get_auth_request(
            fake_auth_request["id"]
        )

        get_replica_result = await auth_request_replica_repo.get_auth_request(
            fake_auth_request["id"]
        )

        assert insert_result.id == get_master_result.id
        assert insert_result.id == get_replica_result.id

        non_existent_id_result = await auth_request_replica_repo.get_auth_request(
            uuid.uuid4()
        )

        assert non_existent_id_result == None
