from datetime import datetime

import pytest
import pytz
from asynctest import MagicMock, CoroutineMock

from app.purchasecard.core.store_metadata.processor import CardPaymentMetadataProcessor


@pytest.mark.asyncio
class TestCardPaymentMetadataProcessor:

    TEST_STORE_ID = "123"
    TEST_MID = "mid"
    TEST_MNAME = "mname"

    @pytest.fixture
    def metadata_processor(self, mock_store_mastercard_data_repo):
        return CardPaymentMetadataProcessor(
            store_mastercard_data_repo=mock_store_mastercard_data_repo
        )

    async def test_create_store_card_payment_metadata(self, metadata_processor):
        updated_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        metadata_processor.store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid = (
            CoroutineMock()
        )
        metadata_processor.store_mastercard_data_repo.update_store_mastercard_data = (
            CoroutineMock()
        )
        metadata_processor.store_mastercard_data_repo.create_store_mastercard_data = (
            CoroutineMock()
        )
        metadata_processor.store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid.return_value = (
            None
        )
        metadata_processor.store_mastercard_data_repo.create_store_mastercard_data.return_value = MagicMock(
            updated_at=updated_at
        )
        result = await metadata_processor.create_or_update_store_card_payment_metadata(
            self.TEST_STORE_ID, self.TEST_MID, self.TEST_MNAME
        )
        assert result.updated_at == str(datetime.timestamp(updated_at))
        metadata_processor.store_mastercard_data_repo.update_store_mastercard_data.assert_not_awaited()

    async def test_update_store_card_payment_metadata(self, metadata_processor):
        updated_at = datetime.utcnow().replace(tzinfo=pytz.utc)
        metadata_processor.store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid = (
            CoroutineMock()
        )
        metadata_processor.store_mastercard_data_repo.update_store_mastercard_data = (
            CoroutineMock()
        )
        metadata_processor.store_mastercard_data_repo.create_store_mastercard_data = (
            CoroutineMock()
        )
        metadata_processor.store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid.return_value = (
            123
        )
        metadata_processor.store_mastercard_data_repo.update_store_mastercard_data.return_value = MagicMock(
            updated_at=updated_at
        )
        result = await metadata_processor.create_or_update_store_card_payment_metadata(
            self.TEST_STORE_ID, self.TEST_MID, self.TEST_MNAME
        )
        metadata_processor.store_mastercard_data_repo.update_store_mastercard_data.assert_awaited()
        metadata_processor.store_mastercard_data_repo.create_store_mastercard_data.assert_not_awaited()
        assert result.updated_at == str(datetime.timestamp(updated_at))
