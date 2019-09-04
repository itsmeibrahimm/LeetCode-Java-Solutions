from typing import Optional

from fastapi import Depends
from psycopg2._psycopg import DataError
from structlog.stdlib import BoundLogger

from app.commons import tracing
from app.commons.context.app_context import AppContext, get_global_app_context
from app.commons.context.req_context import get_logger_from_req
from app.payin.core.dispute.types import DISPUTE_ID_TYPE
from app.payin.core.exceptions import DisputeReadError, PayinErrorCode
from app.payin.core.dispute.model import Dispute
from app.payin.repository.dispute_repo import (
    DisputeRepository,
    GetStripeDisputeByIdInput,
)


@tracing.set_processor_name("disputes", only_trackable=False)
class DisputeClient:
    """
    Dispute client wrapper that provides utilities to dispute.
    """

    def __init__(
        self,
        app_ctxt: AppContext = Depends(get_global_app_context),
        log: BoundLogger = Depends(get_logger_from_req),
        dispute_repo: DisputeRepository = Depends(DisputeRepository.get_repository),
    ):
        self.app_ctxt = app_ctxt
        self.log = log
        self.dispute_repo = dispute_repo

    async def get_dispute_object(
        self, dispute_id: str, dispute_id_type: Optional[str] = None
    ) -> Dispute:
        if dispute_id_type and dispute_id_type not in (
            DISPUTE_ID_TYPE.PGP_DISPUTE_ID,
            DISPUTE_ID_TYPE.STRIPE_DISPUTE_ID,
        ):
            self.log.error(
                f"[get_dispute_object][{dispute_id}] invalid dispute_id_type:[{dispute_id_type}]"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_INVALID_DATA, retryable=False
            )
        try:
            dispute_entity = await self.dispute_repo.get_dispute_by_dispute_id(
                dispute_input=GetStripeDisputeByIdInput(
                    stripe_dispute_id=dispute_id, dispute_id_type=dispute_id_type
                )
            )
        except DataError as e:
            self.log.error(
                f"[get_dispute_entity][{dispute_id} DataError while reading db. {e}"
            )
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_READ_DB_ERROR, retryable=False
            )
        if dispute_entity is None:
            self.log.error("[get_dispute_entity] Dispute not found:[%s]", dispute_id)
            raise DisputeReadError(
                error_code=PayinErrorCode.DISPUTE_NOT_FOUND, retryable=False
            )
        return dispute_entity.to_stripe_dispute()


class DisputeProcessor:
    def __init__(
        self,
        dispute_client: DisputeClient = Depends(DisputeClient),
        log: BoundLogger = Depends(get_logger_from_req),
    ):
        self.dispute_client = dispute_client
        self.log = log

    async def get(self, dispute_id: str, dispute_id_type: Optional[str] = None):
        """
        Retrieve DoorDash dispute

        :param dispute_id: [string] dispute unique id.
        :param dispute_id_type: [string] identify the type of dispute_id. Valid values include "pgp_dispute_id",
               "stripe_dispute_id")
        :return: Dispute object
        """
        self.log.info(
            f"[get] dispute_id:{dispute_id}, dispute_id_type:{dispute_id_type}"
        )
        dispute = await self.dispute_client.get_dispute_object(
            dispute_id=dispute_id, dispute_id_type=dispute_id_type
        )
        return dispute
