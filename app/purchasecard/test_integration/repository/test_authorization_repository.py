import sys
import uuid
from random import randint

import pytest
from typing_extensions import TypedDict

from app.commons.database.infra import DB
from app.purchasecard.models.paymentdb.auth_request_state import AuthRequestStateName
from app.purchasecard.repository.authorization_repository import (
    AuthorizationMasterRepository,
    AuthorizationReplicaRepository,
)
from app.purchasecard.repository.base import NonValidReplicaOperation


class SimpleIntegerIdContainer:
    def __init__(self, num_ids):
        rand_id = randint(-sys.maxsize - 1, sys.maxsize)
        self._ids = [rand_id] * num_ids
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

        assert len(get_auth_state_by_auth_id_master_result) == 1
        assert len(get_auth_state_by_auth_id_replica_result) == 1
        assert auth_state.id == get_auth_state_by_auth_id_master_result[0].id
        assert auth_state.id == get_auth_state_by_auth_id_replica_result[0].id

        non_existent_id_result = await authorization_replica_repo.get_auth_request(
            uuid.uuid4()
        )

        assert non_existent_id_result == None

    async def test_create_auth_request_state_and_update_ttl(
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

        assert auth.expire_sec is None
        assert auth_state.state == AuthRequestStateName.ACTIVE_CREATED

        class AnnoyingMyPyDictTwo(TypedDict):
            state_id: uuid.UUID
            auth_id: uuid.UUID
            state: AuthRequestStateName
            subtotal: int
            subtotal_tax: int

        fake_auth_state_request: AnnoyingMyPyDictTwo = {
            "auth_id": fake_auth_request["auth_id"],
            "state_id": uuid.uuid4(),
            "state": AuthRequestStateName.CLOSED_CONSUMED,
            "subtotal": 300,
            "subtotal_tax": 24,
        }

        create_auth_request_state_result = await authorization_master_repo.create_auth_request_state(
            **fake_auth_state_request
        )

        assert (
            create_auth_request_state_result.state
            == AuthRequestStateName.CLOSED_CONSUMED
        )
        assert (
            create_auth_request_state_result.id == fake_auth_state_request["state_id"]
        )
        assert (
            create_auth_request_state_result.auth_request_id
            == fake_auth_state_request["auth_id"]
        )
        assert (
            create_auth_request_state_result.subtotal
            == fake_auth_state_request["subtotal"]
        )
        assert (
            create_auth_request_state_result.subtotal_tax
            == fake_auth_state_request["subtotal_tax"]
        )

        updated_auth_request = await authorization_master_repo.update_auth_request_ttl(
            shift_id=fake_auth_request["shift_id"],
            delivery_id=fake_auth_request["delivery_id"],
            store_id=fake_auth_request["store_id"],
            ttl=5,
        )

        assert updated_auth_request.created_at != updated_auth_request.updated_at
        assert updated_auth_request.expire_sec == 5

        old_updated_at = updated_auth_request.updated_at

        updated_auth_request = await authorization_master_repo.update_auth_request_ttl(
            shift_id=fake_auth_request["shift_id"],
            delivery_id=fake_auth_request["delivery_id"],
            store_id=fake_auth_request["store_id"],
            ttl=None,
        )

        assert old_updated_at < updated_auth_request.updated_at
        assert updated_auth_request.expire_sec is None

        with pytest.raises(NonValidReplicaOperation):
            await authorization_replica_repo.create_auth_request_state(
                **fake_auth_state_request
            )

        with pytest.raises(NonValidReplicaOperation):
            await authorization_replica_repo.update_auth_request_ttl(
                shift_id=fake_auth_request["shift_id"],
                delivery_id=fake_auth_request["delivery_id"],
                store_id=fake_auth_request["store_id"],
                ttl=None,
            )

    async def test_get_auth_requests_for_shift(
        self,
        authorization_master_repo,
        authorization_replica_repo,
        unique_shift_delivery_store_id_generator: SimpleIntegerIdContainer,
    ):
        ids_one = unique_shift_delivery_store_id_generator.increment_random_id()

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
            "shift_id": str(ids_one[0]),
            "delivery_id": str(ids_one[1]),
            "store_id": str(ids_one[2]),
            "store_city": "Mountain View",
            "store_business_name": "jazzy jasmine tea",
            "subtotal": 3,
            "subtotal_tax": 5,
            "dasher_id": "7",
        }
        auth, auth_state = await authorization_master_repo.create_authorization(
            **fake_auth_request
        )

        assert auth.expire_sec is None
        assert auth_state.state == AuthRequestStateName.ACTIVE_CREATED

        ids_two = unique_shift_delivery_store_id_generator.increment_random_id()

        fake_auth_request_two: AnnoyingMyPyDict = {
            "auth_id": uuid.uuid4(),
            "state_id": uuid.uuid4(),
            "shift_id": str(ids_two[0]),
            "delivery_id": str(ids_two[1]),
            "store_id": str(ids_two[2]),
            "store_city": "Mountain View",
            "store_business_name": "jazzy jasmine tea",
            "subtotal": 3,
            "subtotal_tax": 5,
            "dasher_id": "7",
        }
        auth_2, auth_state_2 = await authorization_master_repo.create_authorization(
            **fake_auth_request_two
        )

        assert auth_2.expire_sec is None
        assert auth_state_2.state == AuthRequestStateName.ACTIVE_CREATED

    async def test_get_auth_request_states_for_multiple_auth_request(
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

        fake_auth_request_one: AnnoyingMyPyDict = {
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

        ids = unique_shift_delivery_store_id_generator.increment_random_id()

        fake_auth_request_two: AnnoyingMyPyDict = {
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

        auth_one, auth_state_one = await authorization_master_repo.create_authorization(
            **fake_auth_request_one
        )

        auth_two, auth_state_two = await authorization_master_repo.create_authorization(
            **fake_auth_request_two
        )

        class AnnoyingMyPyDictTwo(TypedDict):
            state_id: uuid.UUID
            auth_id: uuid.UUID
            state: AuthRequestStateName
            subtotal: int
            subtotal_tax: int

        fake_auth_state_request: AnnoyingMyPyDictTwo = {
            "auth_id": fake_auth_request_two["auth_id"],
            "state_id": uuid.uuid4(),
            "state": AuthRequestStateName.CLOSED_CONSUMED,
            "subtotal": 300,
            "subtotal_tax": 24,
        }

        create_auth_request_state_result = await authorization_master_repo.create_auth_request_state(
            **fake_auth_state_request
        )

        auth_request_states = await authorization_master_repo.get_auth_request_states_for_multiple_auth_request(
            [fake_auth_request_one["auth_id"], fake_auth_request_two["auth_id"]]
        )

        auth_request_states_replica = await authorization_replica_repo.get_auth_request_states_for_multiple_auth_request(
            [fake_auth_request_one["auth_id"], fake_auth_request_two["auth_id"]]
        )

        expected_ids = set(
            [auth_state_one.id, auth_state_two.id, create_auth_request_state_result.id]
        )

        assert expected_ids == set([state.id for state in auth_request_states])
        assert expected_ids == set([state.id for state in auth_request_states_replica])
        assert len(auth_request_states) == 3
        assert len(auth_request_states_replica) == 3

        auth_request_state_one_id = await authorization_master_repo.get_auth_request_states_for_multiple_auth_request(
            [fake_auth_request_one["auth_id"]]
        )
        expected_ids = set([auth_state_one.id])
        assert expected_ids == set([state.id for state in auth_request_state_one_id])
        assert len(auth_request_state_one_id) == 1
