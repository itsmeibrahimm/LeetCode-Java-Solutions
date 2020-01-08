from abc import abstractmethod, ABC
from datetime import datetime
from uuid import UUID

from sqlalchemy import text, select
from typing_extensions import final

from app.commons import tracing
from app.commons.database.infra import DB
from app.purchasecard.models.paymentdb import auth_request_state
from app.purchasecard.models.paymentdb.auth_request_state import (
    AuthRequestStateName,
    AuthRequestState,
)
from app.purchasecard.repository.base import PurchaseCardPaymentDBRepository


class AuthRequestStateRepositoryInterface(ABC):
    @abstractmethod
    async def insert(
        self, *, id: UUID, auth_request_id: UUID, subtotal: int, subtotal_tax: int
    ) -> AuthRequestState:
        pass

    @abstractmethod
    async def get(self, id: UUID) -> AuthRequestState:
        pass

    @abstractmethod
    async def get_by_auth_request_id(self, auth_request_id: UUID) -> AuthRequestState:
        pass


@final
@tracing.track_breadcrumb(repository_name="auth_request_state")
class AuthRequestStateRepository(
    PurchaseCardPaymentDBRepository, AuthRequestStateRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def insert(
        self, *, id: UUID, auth_request_id: UUID, subtotal: int, subtotal_tax: int
    ) -> AuthRequestState:
        now = datetime.utcnow()
        mapped_insertion_values = {
            auth_request_state.id: id,
            auth_request_state.auth_request_id: auth_request_id,
            auth_request_state.created_at: now,
            auth_request_state.updated_at: now,
            auth_request_state.state: AuthRequestStateName.ACTIVE_CREATED,
            auth_request_state.subtotal: subtotal,
            auth_request_state.subtotal_tax: subtotal_tax,
        }
        stmt = (
            auth_request_state.table.insert()
            .values(mapped_insertion_values)
            .returning(*auth_request_state.table.columns.values())
        )

        result = await self._database.master().fetch_one(stmt)
        return AuthRequestState.from_row(result) if result else None

    async def get(self, id: UUID) -> AuthRequestState:
        stmt = select([text("*")]).where(auth_request_state.id == id)

        result = await self._database.master().fetch_one(stmt)

        return AuthRequestState.from_row(result) if result else None

    async def get_by_auth_request_id(self, auth_request_id: UUID) -> AuthRequestState:
        stmt = select([text("*")]).where(
            auth_request_state.auth_request_id == auth_request_id
        )

        result = await self._database.master().fetch_one(stmt)

        return AuthRequestState.from_row(result) if result else None
