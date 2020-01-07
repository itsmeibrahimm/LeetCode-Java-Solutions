import pytest

from app.purchasecard.repository.store_mastercard_data import (
    StoreMastercardDataRepository,
)
from app.purchasecard.test_integration.utils import (
    prepare_and_insert_store_mastercard_data,
)


@pytest.mark.asyncio
class TestStoreMastercardDataRepository:

    TEST_MID_ID = "test mid"
    TEST_MID_ID_2 = "test mid 2"
    TEST_MID_ID_3 = "test mid 3"
    TEST_STORE_ID = 123
    TEST_MNAME = "test name"

    async def test_create_store_mastercard_data(
        self, store_mastercard_data_repo: StoreMastercardDataRepository
    ):
        await prepare_and_insert_store_mastercard_data(
            store_mastercard_data_repo, self.TEST_STORE_ID, self.TEST_MID_ID
        )

    async def test_get_store_mastercard_data_id_by_store_id_and_mid(
        self, store_mastercard_data_repo: StoreMastercardDataRepository
    ):
        await prepare_and_insert_store_mastercard_data(
            store_mastercard_data_repo, self.TEST_STORE_ID, self.TEST_MID_ID_2
        )
        store_mastercard_data_id = await store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid(
            store_id=self.TEST_STORE_ID, mid=self.TEST_MID_ID_2
        )
        assert store_mastercard_data_id
        result = await store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid(
            store_id=self.TEST_STORE_ID, mid=self.TEST_MID_ID_3
        )
        assert not result

    async def test_update_store_mastercard_data(
        self, store_mastercard_data_repo: StoreMastercardDataRepository
    ):
        test_data = await prepare_and_insert_store_mastercard_data(
            store_mastercard_data_repo, self.TEST_STORE_ID, self.TEST_MID_ID
        )
        updated_data = await store_mastercard_data_repo.update_store_mastercard_data(
            store_mastercard_data_id=test_data.id, mname=self.TEST_MNAME
        )
        assert updated_data
        assert updated_data.mname == self.TEST_MNAME
        assert test_data.updated_at < updated_data.updated_at
