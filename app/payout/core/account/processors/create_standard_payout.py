from typing import Union, Optional

from app.commons.context.logger import Log
from app.commons.core.errors import PaymentError, DEFAULT_INTERNAL_ERROR
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.repository.maindb.model.stripe_transfer import StripeTransferCreate
from app.payout.repository.maindb.stripe_transfer import (
    StripeTransferRepositoryInterface,
)
from app.payout.types import PayoutAmountType, PayoutType, PayoutMethodType


class CreateStandardPayoutResponse(OperationResponse):
    pass


class CreateStandardPayoutRequest(OperationRequest):
    payout_account_id: int
    amount: PayoutAmountType
    payout_type: PayoutType = PayoutType.Standard
    transfer_id: Optional[str] = None
    payout_id: Optional[str] = None
    method: Optional[PayoutMethodType]
    submitted_by: Optional[str] = None


class CreateStandardPayout(
    AsyncOperation[CreateStandardPayoutRequest, CreateStandardPayoutResponse]
):
    """
    Processor to create a standard payout.
    """

    stripe_transfer_repo: StripeTransferRepositoryInterface

    def __init__(
        self,
        request: CreateStandardPayoutRequest,
        *,
        stripe_transfer_repo: StripeTransferRepositoryInterface,
        logger: Log = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_transfer_repo = stripe_transfer_repo

    async def _execute(self) -> CreateStandardPayoutResponse:
        self.logger.info(f"CreateStandardPayout")
        stripe_transfer_create = StripeTransferCreate(
            transfer_id=self.request.transfer_id, stripe_status="new"
        )
        stripe_transfer = await self.stripe_transfer_repo.create_stripe_transfer(
            stripe_transfer_create
        )
        self.logger.info(
            f"Created a stripe transfer for StandardPayout. stripe_transfer.id: {stripe_transfer.id}"
        )
        return CreateStandardPayoutResponse()

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentError, CreateStandardPayoutResponse]:
        # TODO write actual exception handling
        raise DEFAULT_INTERNAL_ERROR
