from typing import Optional
from uuid import uuid4

from structlog import BoundLogger

from app.purchasecard.core.auth.models import (
    InternalStoreInfo,
    InternalCreateAuthResponse,
)
from app.purchasecard.marqeta_external.marqeta_provider_client import (
    MarqetaProviderClient,
)
from app.purchasecard.models.paymentdb.auth_request import AuthRequest
from app.purchasecard.repository.auth_request_repository import (
    AuthRequestRepositoryInterface,
)
from app.purchasecard.repository.auth_request_state_repository import (
    AuthRequestStateRepositoryInterface,
)


class AuthProcessor:
    logger: BoundLogger
    marqeta_client: MarqetaProviderClient

    def __init__(
        self,
        logger: BoundLogger,
        marqeta_client: MarqetaProviderClient,
        auth_request_master_repo: AuthRequestRepositoryInterface,
        auth_request_replica_repo: AuthRequestRepositoryInterface,
        auth_request_state_repo: AuthRequestStateRepositoryInterface,
    ):
        self.logger = logger
        self.marqeta_client = marqeta_client
        self.auth_request_master_repo = auth_request_master_repo
        self.auth_request_replica_repo = auth_request_replica_repo
        self.auth_request_state_repo = auth_request_state_repo

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

        # create db entries
        auth_request: AuthRequest = await self.auth_request_master_repo.insert(
            id=auth_request_id,
            shift_id=shift_id,
            delivery_id=delivery_id,
            store_id=store_meta.store_id,
            store_city=store_meta.store_city,
            store_business_name=store_meta.store_business_name,
        )

        auth_request_state_id = uuid4()

        await self.auth_request_state_repo.insert(
            id=auth_request_state_id,
            auth_request_id=auth_request.id,
            subtotal=subtotal,
            subtotal_tax=subtotal_tax,
        )

        return InternalCreateAuthResponse(
            delivery_id=auth_request.delivery_id,
            created_at=auth_request.created_at,
            updated_at=auth_request.updated_at,
        )
