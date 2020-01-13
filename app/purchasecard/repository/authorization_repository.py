from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Tuple, Optional, List
from uuid import UUID

from sqlalchemy import text, and_
from sqlalchemy.sql import select
from typing_extensions import final

from app.commons import tracing
from app.commons.database.client.interface import DBConnection
from app.commons.database.infra import DB
from app.purchasecard.models.paymentdb import auth_request, auth_request_state
from app.purchasecard.models.paymentdb.auth_request import AuthRequest
from app.purchasecard.models.paymentdb.auth_request_state import (
    AuthRequestStateName,
    AuthRequestState,
)
from app.purchasecard.repository.base import (
    PurchaseCardPaymentDBRepository,
    NonValidReplicaOperation,
)


class AuthorizationRepositoryInterface(ABC):
    @abstractmethod
    async def create_authorization(
        self,
        *,
        auth_id: UUID,
        state_id: UUID,
        shift_id: str,
        delivery_id: str,
        store_id: str,
        store_city: str,
        store_business_name: str,
        subtotal: int,
        subtotal_tax: int,
        dasher_id: str = None,
    ) -> Tuple[AuthRequest, AuthRequestState]:
        pass

    @abstractmethod
    async def create_auth_request_state(
        self,
        *,
        state_id: UUID,
        auth_id: UUID,
        state: str,
        subtotal: int,
        subtotal_tax: int,
    ) -> AuthRequestState:
        pass

    @abstractmethod
    async def get_auth_request(self, id: UUID) -> Optional[AuthRequest]:
        pass

    @abstractmethod
    async def get_auth_request_state(self, id: UUID) -> Optional[AuthRequestState]:
        pass

    @abstractmethod
    async def get_auth_request_state_by_auth_id(
        self, auth_request_id: UUID
    ) -> List[AuthRequestState]:
        pass

    @abstractmethod
    async def get_auth_request_by_delivery_shift_combination(
        self, delivery_id: str, shift_id: str
    ) -> Optional[AuthRequest]:
        pass

    @abstractmethod
    async def update_auth_request_ttl(
        self, shift_id: str, delivery_id: str, store_id: str, ttl: int
    ) -> Optional[AuthRequest]:
        pass


@final
@tracing.track_breadcrumb(repository_name="auth_request")
class AuthorizationMasterRepository(
    PurchaseCardPaymentDBRepository, AuthorizationRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_authorization(
        self,
        *,
        auth_id: UUID,
        state_id: UUID,
        shift_id: str,
        delivery_id: str,
        store_id: str,
        store_city: str,
        store_business_name: str,
        subtotal: int,
        subtotal_tax: int,
        dasher_id: str = None,
    ) -> Tuple[AuthRequest, AuthRequestState]:
        now = datetime.now(timezone.utc)

        auth_request_insertion_values = {
            auth_request.id: auth_id,
            auth_request.created_at: now,
            auth_request.updated_at: now,
            auth_request.shift_id: shift_id,
            auth_request.delivery_id: delivery_id,
            auth_request.dasher_id: dasher_id,
            auth_request.store_id: store_id,
            auth_request.store_city: store_city,
            auth_request.store_business_name: store_business_name,
        }

        auth_request_state_insertion_values = {
            auth_request_state.id: state_id,
            auth_request_state.auth_request_id: auth_id,
            auth_request_state.created_at: now,
            auth_request_state.updated_at: now,
            auth_request_state.state: AuthRequestStateName.ACTIVE_CREATED,
            auth_request_state.subtotal: subtotal,
            auth_request_state.subtotal_tax: subtotal_tax,
        }

        auth_request_insertion_stmt = (
            auth_request.table.insert()
            .values(auth_request_insertion_values)
            .returning(*auth_request.table.columns.values())
        )

        auth_request_state_insertion_stmt = (
            auth_request_state.table.insert()
            .values(auth_request_state_insertion_values)
            .returning(*auth_request_state.table.columns.values())
        )

        async with self._database.master().transaction() as tx:
            connection: DBConnection = tx.connection()
            auth_result = await connection.execute(auth_request_insertion_stmt)

            auth_state_result = await connection.execute(
                auth_request_state_insertion_stmt
            )

        auth_request_entity = AuthRequest.from_row(auth_result[0])
        auth_request_state_entity = AuthRequestState.from_row(auth_state_result[0])

        return auth_request_entity, auth_request_state_entity

    async def create_auth_request_state(
        self,
        *,
        state_id: UUID,
        auth_id: UUID,
        subtotal: int,
        subtotal_tax: int,
        state: str,
    ) -> AuthRequestState:
        now = datetime.now(timezone.utc)

        auth_request_state_insertion_values = {
            auth_request_state.id: state_id,
            auth_request_state.auth_request_id: auth_id,
            auth_request_state.created_at: now,
            auth_request_state.updated_at: now,
            auth_request_state.state: state,
            auth_request_state.subtotal: subtotal,
            auth_request_state.subtotal_tax: subtotal_tax,
        }

        auth_request_state_insertion_stmt = (
            auth_request_state.table.insert()
            .values(auth_request_state_insertion_values)
            .returning(*auth_request_state.table.columns.values())
        )

        auth_request_state_result = await self._database.master().execute(
            auth_request_state_insertion_stmt
        )

        return AuthRequestState.from_row(auth_request_state_result[0])

    async def get_auth_request(self, id: UUID) -> Optional[AuthRequest]:
        stmnt = select([text("*")]).where(auth_request.id == id)

        result = await self._database.master().fetch_one(stmnt)

        return AuthRequest.from_row(result) if result else None

    async def get_auth_request_state(self, id: UUID) -> Optional[AuthRequestState]:
        stmt = select([text("*")]).where(auth_request_state.id == id)

        result = await self._database.master().fetch_one(stmt)

        return AuthRequestState.from_row(result) if result else None

    async def get_auth_request_state_by_auth_id(
        self, auth_request_id: UUID
    ) -> List[AuthRequestState]:
        stmt = select([text("*")]).where(
            auth_request_state.auth_request_id == auth_request_id
        )

        results = await self._database.master().fetch_all(stmt)

        return [AuthRequestState.from_row(result) for result in results]

    async def get_auth_request_by_delivery_shift_combination(
        self, delivery_id: str, shift_id: str
    ) -> Optional[AuthRequest]:
        stmnt = select([text("*")]).where(
            and_(
                auth_request.delivery_id == delivery_id,
                auth_request.shift_id == shift_id,
            )
        )

        result = await self._database.master().fetch_one(stmnt)

        return AuthRequest.from_row(result) if result else None

    async def update_auth_request_ttl(
        self, shift_id: str, delivery_id: str, store_id: str, ttl: int
    ) -> Optional[AuthRequest]:
        now = datetime.now(timezone.utc)
        auth_request_update_values = {
            auth_request.expire_sec: ttl,
            auth_request.updated_at: now,
        }

        statement = (
            auth_request.table.update()
            .where(
                and_(
                    auth_request.delivery_id == delivery_id,
                    auth_request.shift_id == shift_id,
                    auth_request.store_id == store_id,
                )
            )
            .values(auth_request_update_values)
            .returning(*auth_request.table.columns.values())
        )
        result = await self._database.master().fetch_one(statement)
        return AuthRequest.from_row(result) if result else None


@final
@tracing.track_breadcrumb(repository_name="auth_request")
class AuthorizationReplicaRepository(
    PurchaseCardPaymentDBRepository, AuthorizationRepositoryInterface
):
    def __init__(self, database: DB):
        super().__init__(_database=database)

    async def create_authorization(
        self,
        *,
        auth_id: UUID,
        state_id: UUID,
        shift_id: str,
        delivery_id: str,
        store_id: str,
        store_city: str,
        store_business_name: str,
        subtotal: int,
        subtotal_tax: int,
        dasher_id: str = None,
    ) -> Tuple[AuthRequest, AuthRequestState]:
        raise NonValidReplicaOperation()

    async def create_auth_request_state(
        self,
        *,
        state_id: UUID,
        auth_id: UUID,
        state: str,
        subtotal: int,
        subtotal_tax: int,
    ) -> AuthRequestState:
        raise NonValidReplicaOperation()

    async def get_auth_request(self, id: UUID) -> Optional[AuthRequest]:
        stmnt = select([text("*")]).where(auth_request.id == id)

        result = await self._database.replica().fetch_one(stmnt)

        return AuthRequest.from_row(result) if result else None

    async def get_auth_request_state(self, id: UUID) -> Optional[AuthRequestState]:
        stmt = select([text("*")]).where(auth_request_state.id == id)

        result = await self._database.replica().fetch_one(stmt)

        return AuthRequestState.from_row(result) if result else None

    async def get_auth_request_state_by_auth_id(
        self, auth_request_id: UUID
    ) -> List[AuthRequestState]:
        stmt = select([text("*")]).where(
            auth_request_state.auth_request_id == auth_request_id
        )

        results = await self._database.replica().fetch_all(stmt)

        return [AuthRequestState.from_row(result) for result in results]

    async def get_auth_request_by_delivery_shift_combination(
        self, delivery_id: str, shift_id: str
    ) -> Optional[AuthRequest]:
        stmnt = select([text("*")]).where(
            and_(
                auth_request.delivery_id == delivery_id,
                auth_request.shift_id == shift_id,
            )
        )

        result = await self._database.replica().fetch_one(stmnt)

        return AuthRequest.from_row(result) if result else None

    async def update_auth_request_ttl(
        self, shift_id: str, delivery_id: str, store_id: str, ttl: int
    ) -> Optional[AuthRequest]:
        raise NonValidReplicaOperation()
