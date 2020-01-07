from datetime import datetime

from app.purchasecard.core.errors import (
    StoreMastercardDataNotFoundError,
    StoreMetadataInvalidInputError,
)
from app.purchasecard.core.store_metadata.models import InternalStoreCardPaymentMetadata
from app.purchasecard.repository.store_mastercard_data import (
    StoreMastercardDataRepositoryInterface,
)


class CardPaymentMetadataProcessor:
    def __init__(
        self, store_mastercard_data_repo: StoreMastercardDataRepositoryInterface
    ):
        self.store_mastercard_data_repo = store_mastercard_data_repo

    async def create_or_update_store_card_payment_metadata(
        self, store_id: str, mid: str, mname: str
    ) -> InternalStoreCardPaymentMetadata:
        try:
            parsed_store_id = int(store_id)
        except ValueError:
            raise StoreMetadataInvalidInputError()

        existing_record_id = await self.store_mastercard_data_repo.get_store_mastercard_data_id_by_store_id_and_mid(
            store_id=parsed_store_id, mid=mid
        )
        if existing_record_id:
            result = await self.store_mastercard_data_repo.update_store_mastercard_data(
                store_mastercard_data_id=existing_record_id, mname=mname
            )
            if not result:
                raise StoreMastercardDataNotFoundError()

        else:
            result = await self.store_mastercard_data_repo.create_store_mastercard_data(
                store_id=parsed_store_id, mid=mid, mname=mname
            )
        return InternalStoreCardPaymentMetadata(
            updated_at=datetime.timestamp(result.updated_at)
        )
