from typing import Union

from app.commons.context.logger import Log
from app.commons.core.errors import PaymentError, DEFAULT_INTERNAL_ERROR
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.repository.maindb.model.payment_account import (
    PaymentAccount,
    PaymentAccountCreate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class CreatePayoutAccountResponse(OperationResponse):
    payment_account: PaymentAccount


class CreatePayoutAccountRequest(OperationRequest):
    statement_descriptor: str = "DoorDash, Inc."


class CreatePayoutAccount(
    AsyncOperation[CreatePayoutAccountRequest, CreatePayoutAccountResponse]
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

    async def _execute(self) -> CreatePayoutAccountResponse:
        payment_account_create = PaymentAccountCreate(**self.request.dict())
        payment_account = await self.payment_account_repo.create_payment_account(
            payment_account_create
        )
        return CreatePayoutAccountResponse(payment_account=payment_account)

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentError, CreatePayoutAccountResponse]:
        # TODO write actual exception handling
        raise DEFAULT_INTERNAL_ERROR
