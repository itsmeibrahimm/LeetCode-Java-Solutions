from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.maindb import store_mastercard_data
from app.purchasecard.models.maindb.store_mastercard_data import StoreMastercardData
from app.purchasecard.repository.base import PurchaseCardMainDBRepository


class StoreMastercardDataRepositoryInterface(ABC):
    @abstractmethod
    async def create_store_mastercard_data(
        self, store_id: int, mid: str, mname: str = None
    ) -> StoreMastercardData:
        pass

    @abstractmethod
    async def update_store_mastercard_data(
        self, store_mastercard_data_id: int, mname: str = None
    ) -> Optional[StoreMastercardData]:
        pass

    @abstractmethod
    async def get_store_mastercard_data_id_by_store_id_and_mid(
        self, store_id: int, mid: str
    ) -> Optional[int]:
        pass


@final
@tracing.track_breadcrumb(repository_name="store_mastercard_data")
class StoreMastercardDataRepository(
    PurchaseCardMainDBRepository, StoreMastercardDataRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_store_mastercard_data(
        self, store_id: int, mid: str, mname: str = None
    ) -> StoreMastercardData:
        stmt = (
            store_mastercard_data.table.insert()
            .values(
                store_id=store_id,
                mid=mid,
                updated_at=datetime.now(timezone.utc),
                mname=mname,
            )
            .returning(*store_mastercard_data.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        assert row is not None
        return StoreMastercardData.from_row(row)

    async def update_store_mastercard_data(
        self, store_mastercard_data_id: int, mname: str = None
    ) -> Optional[StoreMastercardData]:
        stmt = (
            store_mastercard_data.table.update()
            .where(store_mastercard_data.id == store_mastercard_data_id)
            .values(mname=mname, updated_at=datetime.now(timezone.utc))
            .returning(*store_mastercard_data.table.columns.values())
        )
        row = await self._database.master().fetch_one(stmt)
        return StoreMastercardData.from_row(row) if row else None

    async def get_store_mastercard_data_id_by_store_id_and_mid(
        self, store_id: int, mid: str
    ) -> Optional[int]:
        stmt = store_mastercard_data.table.count().where(
            and_(
                store_mastercard_data.store_id == store_id,
                store_mastercard_data.mid == mid,
            )
        )
        result = await self._database.replica().fetch_value(stmt)
        return result if result else None
