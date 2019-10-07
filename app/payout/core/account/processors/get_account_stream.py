from structlog.stdlib import BoundLogger
from typing import List, Optional, Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import (
    AsyncOperation,
    OperationRequest,
    OperationResponse,
)
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class GetPayoutAccountStreamRequest(OperationRequest):
    offset: int = 0
    limit: int = 10


class GetPayoutAccountStreamResponse(OperationResponse):
    new_offset: Optional[int]
    items: List[PayoutAccountInternal]


class GetPayoutAccountStream(
    AsyncOperation[GetPayoutAccountStreamRequest, GetPayoutAccountStreamResponse]
):
    """
    Processor to get a payout account stream
    """

    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: GetPayoutAccountStreamRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo

    async def _execute(self) -> GetPayoutAccountStreamResponse:
        payment_accounts = await self.payment_account_repo.get_all_payment_accounts(
            offset=self.request.offset, limit=self.request.limit
        )

        account_ids = [a.account_id for a in payment_accounts if a.account_id]
        stripe_managed_accounts_by_id = await self.payment_account_repo.get_stripe_managed_account_by_ids(
            account_ids
        )

        items: List[PayoutAccountInternal] = []
        for payment_account in payment_accounts:
            pgp_external_account_id: Optional[str] = None
            if payment_account.account_id:
                stripe_managed_account = stripe_managed_accounts_by_id.get(
                    payment_account.account_id, None
                )
                if stripe_managed_account:
                    pgp_external_account_id = stripe_managed_account.stripe_id

            payout_account = PayoutAccountInternal(
                payment_account=payment_account,
                pgp_external_account_id=pgp_external_account_id,
            )
            items.append(payout_account)

        new_offset: Optional[int] = None
        if len(items) >= self.request.limit:
            new_offset = self.request.offset + self.request.limit

        return GetPayoutAccountStreamResponse(new_offset=new_offset, items=items)

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, GetPayoutAccountStreamResponse]:
        raise DEFAULT_INTERNAL_EXCEPTION
