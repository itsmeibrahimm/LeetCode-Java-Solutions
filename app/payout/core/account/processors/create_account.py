from structlog.stdlib import BoundLogger
from typing import Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.repository.maindb.model.payment_account import PaymentAccountCreate
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.types import PayoutAccountTargetType


class CreatePayoutAccountRequest(OperationRequest):
    entity: PayoutAccountTargetType
    statement_descriptor: str = "DoorDash, Inc."


class CreatePayoutAccount(
    AsyncOperation[CreatePayoutAccountRequest, PayoutAccountInternal]
):
    """
    Processor to create a payout account
    """

    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: CreatePayoutAccountRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo

    async def _execute(self) -> PayoutAccountInternal:
        payment_account_create = PaymentAccountCreate(**self.request.dict())
        payment_account = await self.payment_account_repo.create_payment_account(
            payment_account_create
        )
        # todo: PAY-3566 implement the verification_requirements
        return PayoutAccountInternal(payment_account=payment_account)

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
