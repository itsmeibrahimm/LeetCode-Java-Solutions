from uuid import uuid4

import pytest

from app.commons.database.infra import DB
from app.purchasecard.models.maindb.store_mastercard_data import StoreMastercardData
from app.purchasecard.repository.store_mastercard_data import (
    StoreMastercardDataRepository,
)
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_store_mastercard_data,
)


@pytest.mark.asyncio
class TestStoreMastercardDataRepository:

    TEST_STORE_ID = 123
    TEST_MNAME = "test name"

    @pytest.fixture
    def store_mastercard_data_repo(
        self, purchasecard_maindb: DB
    ) -> StoreMastercardDataRepository:
        return StoreMastercardDataRepository(database=purchasecard_maindb)

    @pytest.fixture
    async def created_store_mastercard_data(
        self, store_mastercard_data_repo
    ) -> StoreMastercardData:
        return await prepare_and_insert_store_mastercard_data(
            store_mastercard_data_repo, store_id=self.TEST_STORE_ID, mid=str(uuid4())
        )

    async def test_create_store_mastercard_data(
        self, store_mastercard_data_repo: StoreMastercardDataRepository
    ):
        await prepare_and_insert_store_mastercard_data(
            store_mastercard_data_repo, self.TEST_STORE_ID, str(uuid4())
        )

    async def test_get_or_create_store_mastercard_data(
        self,
        store_mastercard_data_repo: StoreMastercardDataRepository,
        created_store_mastercard_data: StoreMastercardData,
    ):
        expected = await store_mastercard_data_repo.get_store_mastercard_data_by_store_id_and_mid(
            store_id=created_store_mastercard_data.store_id,
            mid=created_store_mastercard_data.mid,
        )
        assert expected
        actual = await store_mastercard_data_repo.get_or_create_store_mastercard_data(
            store_id=created_store_mastercard_data.store_id,
            mid=created_store_mastercard_data.mid,
        )
        assert actual.id == expected.id
        actual = await store_mastercard_data_repo.get_or_create_store_mastercard_data(
            store_id=self.TEST_STORE_ID, mid=str(uuid4())
        )
        assert actual.id
        assert not actual.id == expected.id

    async def test_update_store_mastercard_data(
        self, store_mastercard_data_repo: StoreMastercardDataRepository
    ):
        test_data = await prepare_and_insert_store_mastercard_data(
            store_mastercard_data_repo, self.TEST_STORE_ID, str(uuid4())
        )
        updated_data = await store_mastercard_data_repo.update_store_mastercard_data(
            store_mastercard_data_id=test_data.id, mname=self.TEST_MNAME
        )
        assert updated_data
        assert updated_data.mname == self.TEST_MNAME
        assert test_data.updated_at < updated_data.updated_at
