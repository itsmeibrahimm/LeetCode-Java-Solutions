from app.purchasecard.core.store_metadata.models import InternalStoreCardPaymentMetadata
from app.purchasecard.core.utils import enriched_error_parse_int
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
        parsed_store_id = enriched_error_parse_int(store_id, "store id")

        result = await self.store_mastercard_data_repo.get_or_create_store_mastercard_data(
            store_id=parsed_store_id, mid=mid, mname=mname
        )
        return InternalStoreCardPaymentMetadata(updated_at=result.updated_at)
