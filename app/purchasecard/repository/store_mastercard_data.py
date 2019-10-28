from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


@final
@tracing.track_breadcrumb(repository_name="store_mastercard_data")
class StoreMastercardDataRepository(PurchaseCardMainDBRepository):
    def __init__(self, database: DB):
        super().__init__(_database=database)
