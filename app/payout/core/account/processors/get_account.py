from structlog.stdlib import BoundLogger
from typing import Optional, Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.account import models as account_models
from app.payout.core.exceptions import payout_account_not_found_error
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.models import PayoutAccountId


class GetPayoutAccountRequest(OperationRequest):
    payout_account_id: PayoutAccountId


class GetPayoutAccount(
    AsyncOperation[GetPayoutAccountRequest, account_models.PayoutAccountInternal]
):
    """
    Processor to get a payout account
    """

    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: GetPayoutAccountRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo

    async def _execute(self) -> account_models.PayoutAccountInternal:
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            self.request.payout_account_id
        )
        if not payment_account:
            raise payout_account_not_found_error()
        stripe_managed_account: Optional[StripeManagedAccount] = None
        if payment_account and payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
        # todo: PAY-3566 implement the verification_requirements
        return account_models.PayoutAccountInternal(
            payment_account=payment_account,
            pgp_external_account_id=stripe_managed_account.stripe_id
            if stripe_managed_account
            else None,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
