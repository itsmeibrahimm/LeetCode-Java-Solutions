from abc import ABC, abstractmethod
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.sql import select
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.paymentdb import auth_request
from app.purchasecard.models.paymentdb.auth_request import AuthRequest
from app.purchasecard.repository.base import (
    PurchaseCardPaymentDBRepository,
    NonValidReplicaOperation,
)


class AuthRequestRepositoryInterface(ABC):
    @abstractmethod
    async def insert(
        self,
        *,
        id: UUID,
        shift_id: str,
        delivery_id: str,
        store_id: str,
        store_city: str,
        store_business_name: str,
        dasher_id: str = None,
    ):
        pass

    @abstractmethod
    async def get_auth_request(self, id: UUID):
        pass


@final
@tracing.track_breadcrumb(repository_name="auth_request")
class AuthRequestMasterRepository(
    PurchaseCardPaymentDBRepository, AuthRequestRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def insert(
        self,
        *,
        id: UUID,
        shift_id: str,
        delivery_id: str,
        store_id: str,
        store_city: str,
        store_business_name: str,
        dasher_id: str = None,
    ):
        now = datetime.now(timezone.utc)
        mapped_insertion_values = {
            auth_request.id: id,
            auth_request.created_at: now,
            auth_request.updated_at: now,
            auth_request.shift_id: shift_id,
            auth_request.delivery_id: delivery_id,
            auth_request.dasher_id: dasher_id,
            auth_request.store_id: store_id,
            auth_request.store_city: store_city,
            auth_request.store_business_name: store_business_name,
        }

        stmnt = (
            auth_request.table.insert()
            .values(mapped_insertion_values)
            .returning(*auth_request.table.columns.values())
        )

        result = await self._database.master().fetch_one(stmnt)
        return AuthRequest.from_row(result) if result else None

    async def get_auth_request(self, id: UUID):
        stmnt = select([text("*")]).where(auth_request.id == id)

        result = await self._database.master().fetch_one(stmnt)

        return AuthRequest.from_row(result) if result else None


@final
@tracing.track_breadcrumb(repository_name="auth_request")
class AuthRequestReplicaRepository(
    PurchaseCardPaymentDBRepository, AuthRequestRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def insert(
        self,
        *,
        id: UUID,
        shift_id: str,
        delivery_id: str,
        store_id: str,
        store_city: str,
        store_business_name: str,
        dasher_id: str = None,
    ):
        raise NonValidReplicaOperation()

    async def get_auth_request(self, id: UUID):
        stmnt = select([text("*")]).where(auth_request.id == id)

        result = await self._database.replica().fetch_one(stmnt)

        return AuthRequest.from_row(result) if result else None
