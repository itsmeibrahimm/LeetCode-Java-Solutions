from itertools import filterfalse
from typing import Optional, List
from uuid import uuid4

from structlog import BoundLogger

from app.purchasecard.core.auth.models import (
    InternalStoreInfo,
    InternalCreateAuthResponse,
    UpdatedAuthorization,
)
from app.purchasecard.core.errors import (
    AuthRequestNotFoundError,
    AuthRequestInconsistentStateError,
)
from app.purchasecard.marqeta_external.marqeta_provider_client import (
    MarqetaProviderClient,
)
from app.purchasecard.models.paymentdb.auth_request import AuthRequest
from app.purchasecard.models.paymentdb.auth_request_state import (
    AuthRequestStateName,
    AuthRequestState,
)
from app.purchasecard.repository.authorization_repository import (
    AuthorizationRepositoryInterface,
)


class AuthProcessor:
    logger: BoundLogger
    marqeta_client: MarqetaProviderClient

    def __init__(
        self,
        logger: BoundLogger,
        marqeta_client: MarqetaProviderClient,
        authorization_master_repo: AuthorizationRepositoryInterface,
        authorization_replica_repo: AuthorizationRepositoryInterface,
    ):
        self.logger = logger
        self.marqeta_client = marqeta_client
        self.authorization_master_repo = authorization_master_repo
        self.authorization_replica_repo = authorization_replica_repo

    async def create_auth(
        self,
        subtotal: int,
        subtotal_tax: int,
        store_meta: InternalStoreInfo,
        delivery_id: str,
        delivery_requires_purchase_card: bool,
        shift_id: str,
        ttl: Optional[int],
    ) -> InternalCreateAuthResponse:
        # generate random auth_request_id
        auth_request_id = uuid4()
        auth_request_state_id = uuid4()

        # create db entries
        auth_request, _ = await self.authorization_master_repo.create_authorization(
            auth_id=auth_request_id,
            state_id=auth_request_state_id,
            shift_id=shift_id,
            delivery_id=delivery_id,
            store_id=store_meta.store_id,
            store_city=store_meta.store_city,
            store_business_name=store_meta.store_business_name,
            subtotal=subtotal,
            subtotal_tax=subtotal_tax,
        )

        return InternalCreateAuthResponse(
            delivery_id=auth_request.delivery_id,
            created_at=auth_request.created_at,
            updated_at=auth_request.updated_at,
        )

    async def update_auth(
        self,
        subtotal: int,
        subtotal_tax: int,
        store_id: str,
        store_city: str,
        store_business_name: str,
        delivery_id: str,
        shift_id: str,
        ttl: Optional[int],
    ) -> UpdatedAuthorization:
        if ttl:
            auth_request = await self.authorization_master_repo.update_auth_request_ttl(
                shift_id=shift_id, delivery_id=delivery_id, store_id=store_id, ttl=ttl
            )
        else:
            auth_request = await self.authorization_master_repo.get_auth_request_by_delivery_shift_combination(
                delivery_id=delivery_id, shift_id=shift_id
            )

        if not auth_request:
            raise AuthRequestNotFoundError()

        auth_request_state_id = uuid4()

        auth_request_state = await self.authorization_master_repo.create_auth_request_state(
            state_id=auth_request_state_id,
            auth_id=auth_request.id,
            subtotal=subtotal,
            subtotal_tax=subtotal_tax,
            state=AuthRequestStateName.ACTIVE_UPDATED,
        )

        return UpdatedAuthorization(
            updated_at=auth_request.updated_at,
            state=auth_request_state.state,
            delivery_id=delivery_id,
            shift_id=shift_id,
        )

    async def close_auth(self, delivery_id: str, shift_id: str) -> AuthRequestStateName:
        auth_request: Optional[
            AuthRequest
        ] = await self.authorization_master_repo.get_auth_request_by_delivery_shift_combination(
            delivery_id=delivery_id, shift_id=shift_id
        )

        if not auth_request:
            raise AuthRequestNotFoundError()

        auth_request_states: List[
            AuthRequestState
        ] = await self.authorization_master_repo.get_auth_request_state_by_auth_id(
            auth_request_id=auth_request.id
        )

        def sort_date(val: AuthRequestState):
            return val.created_at

        if len(auth_request_states) == 0:
            raise AuthRequestInconsistentStateError()

        # Getting the latest auth request state. There should be a limited amount of these states and adding a compound index
        # may not be worth it. TBD
        auth_request_states.sort(key=sort_date, reverse=True)

        created_state: AuthRequestState = await self.authorization_master_repo.create_auth_request_state(
            state_id=uuid4(),
            auth_id=auth_request.id,
            state=AuthRequestStateName.CLOSED_MANUAL,
            subtotal=auth_request_states[0].subtotal,
            subtotal_tax=auth_request_states[0].subtotal_tax,
        )

        return created_state.state

    async def close_all_auth(self, shift_id: str) -> List[AuthRequestStateName]:
        auth_requests: List[
            AuthRequest
        ] = await self.authorization_master_repo.get_auth_requests_for_shift(
            shift_id=shift_id
        )

        ids = [auth_request.id for auth_request in auth_requests]

        jumbled_auth_request_states: List[
            AuthRequestState
        ] = await self.authorization_master_repo.get_auth_request_states_for_multiple_auth_request(
            ids
        )

        results = []

        for auth_request in auth_requests:
            relevant_states = [
                auth_request_state
                for auth_request_state in filterfalse(
                    lambda state: state.auth_request_id != auth_request.id,
                    jumbled_auth_request_states,
                )
            ]

            latest_state = AuthProcessor._get_latest_auth_request_state(relevant_states)

            if latest_state.state != AuthRequestStateName.CLOSED_MANUAL:
                created_state: AuthRequestState = await self.authorization_master_repo.create_auth_request_state(
                    state_id=uuid4(),
                    auth_id=auth_request.id,
                    state=AuthRequestStateName.CLOSED_MANUAL,
                    subtotal=latest_state.subtotal,
                    subtotal_tax=latest_state.subtotal_tax,
                )
                results.append(created_state.state)

        return results

    @classmethod
    def _get_latest_auth_request_state(
        self, auth_request_states: List[AuthRequestState]
    ):
        def sort_date(val: AuthRequestState):
            return val.created_at

        auth_request_states.sort(key=sort_date, reverse=True)

        return auth_request_states[0]
