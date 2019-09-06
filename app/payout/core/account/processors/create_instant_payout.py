import uuid
from datetime import datetime
from typing import Union, Optional

from app.commons.context.logger import Log
from app.commons.core.errors import PaymentError, DEFAULT_INTERNAL_ERROR
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
)
from app.payout.types import (
    PayoutAmountType,
    PayoutType,
    PayoutMethodType,
    PayoutAccountId,
)


class CreateInstantPayoutResponse(OperationResponse):
    pass


class CreateInstantPayoutRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.Standard
    payout_id: Optional[str] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


class CreateInstantPayout(
    AsyncOperation[CreateInstantPayoutRequest, CreateInstantPayoutResponse]
):
    """
    Processor to create a standard payout.
    """

    stripe_payout_request_repo: StripePayoutRequestRepositoryInterface

    def __init__(
        self,
        request: CreateInstantPayoutRequest,
        *,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        logger: Log = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_payout_request_repo = stripe_payout_request_repo

    async def _execute(self) -> CreateInstantPayoutResponse:
        self.logger.info(f"CreatedInstantPayout")
        now = datetime.utcnow()
        # TODO: StripePayoutRequestCreate should enforce required columns
        stripe_payout_request_create = StripePayoutRequestCreate(
            payout_id=self.request.payout_id,
            idempotency_key=str(uuid.uuid4()),
            payout_method_id=1,
            created_at=now,
            updated_at=now,
            status="new",
        )
        stripe_payout_request = await self.stripe_payout_request_repo.create_stripe_payout_request(
            stripe_payout_request_create
        )
        self.logger.info(
            f"Created a stripe payout request for InstantPayout. stripe_payout_request.id: {stripe_payout_request.id}"
        )
        return CreateInstantPayoutResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentError, CreateInstantPayoutResponse]:
        # TODO write actual exception handling
        raise DEFAULT_INTERNAL_ERROR
