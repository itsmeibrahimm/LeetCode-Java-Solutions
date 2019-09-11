from typing import Union

from app.commons.context.logger import Log
from app.commons.core.errors import PaymentError, DEFAULT_INTERNAL_ERROR
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.repository.maindb.model.payment_account import PaymentAccountCreate
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class CreatePayoutAccountRequest(OperationRequest):
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
        logger: Log = None
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
    ) -> Union[PaymentError, PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_ERROR
