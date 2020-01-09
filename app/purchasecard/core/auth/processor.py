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
