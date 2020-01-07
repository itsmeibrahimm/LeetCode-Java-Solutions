from datetime import datetime

import pytest
import pytz
from asynctest import MagicMock, patch, asynctest

from app.purchasecard.core.store_metadata.processor import CardPaymentMetadataProcessor


@pytest.mark.asyncio
class TestCardPaymentMetadataProcessor:

    TEST_STORE_ID = "123"
    TEST_MID = "mid"
    TEST_MNAME = "mname"

    @pytest.fixture
    def metadata_processor(self, store_mastercard_data_repo):
        return CardPaymentMetadataProcessor(
            store_mastercard_data_repo=store_mastercard_data_repo
        )

    @patch(
        "app.purchasecard.repository.store_mastercard_data.StoreMastercardDataRepository.create_store_mastercard_data",
        scope=asynctest.LIMITED,
    )
    @patch(
        "app.purchasecard.repository.store_mastercard_data.StoreMastercardDataRepository.update_store_mastercard_data",
        scope=asynctest.LIMITED,
    )
    @patch(
        "app.purchasecard.repository.store_mastercard_data.StoreMastercardDataRepository"
        ".get_store_mastercard_data_id_by_store_id_and_mid",
        scope=asynctest.LIMITED,
    )
    async def test_store_card_payment_metadata(
        self,
        mock_get_function,
        mock_update_function,
        mock_create_function,
        metadata_processor,
    ):
        mock_get_function.return_value = None
        mock_create_function.return_value = MagicMock(
            updated_at=datetime.utcnow().replace(tzinfo=pytz.utc)
        )
        await metadata_processor.create_or_update_store_card_payment_metadata(
            self.TEST_STORE_ID, self.TEST_MID, self.TEST_MNAME
        )
        mock_create_function.assert_awaited()
        mock_update_function.assert_not_awaited()

        mock_create_function.reset_mock()
        mock_update_function.reset_mock()

        mock_get_function.return_value = 123
        mock_update_function.return_value = MagicMock(
            updated_at=datetime.utcnow().replace(tzinfo=pytz.utc)
        )
        await metadata_processor.create_or_update_store_card_payment_metadata(
            self.TEST_STORE_ID, self.TEST_MID, self.TEST_MNAME
        )
        mock_update_function.assert_awaited()
        mock_create_function.assert_not_awaited()
