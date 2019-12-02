from typing import Union, Optional
import pytz
from structlog import BoundLogger
from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.payout.core.instant_payout.models import (
    GetPayoutStreamRequest,
    GetPayoutStreamResponse,
    PayoutStreamItem,
)
from app.payout.repository.bankdb.payout import PayoutRepositoryInterface
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)


class GetPayoutStream(AsyncOperation[GetPayoutStreamRequest, GetPayoutStreamResponse]):
    """Get Instant Payouts by payout account id.

    Get instant payout records given payout account id, limit, and offset.

    :param request: get instant payout stream request
    :type request: GetPayoutStreamRequest
    :return: instant payout stream: list of instant payout records
    :rtype: instant Payout stream: GetPayoutStreamResponse
    """

    def __init__(
        self,
        request: GetPayoutStreamRequest,
        payout_repo: PayoutRepositoryInterface,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payout_repo = payout_repo
        self.stripe_payout_request_repo = stripe_payout_request_repo

    async def _execute(self) -> GetPayoutStreamResponse:

        payouts = await self.payout_repo.list_payout_by_payout_account_id(
            payout_account_id=self.request.payout_account_id,
            offset=self.request.offset,
            limit=self.request.limit,
        )
        payout_ids = [payout.id for payout in payouts]
        stripe_payout_requests = await self.stripe_payout_request_repo.list_stripe_payout_requests_by_payout_ids(
            payout_ids=payout_ids
        )
        payouts_count = len(payouts)
        # Sort stripe_payout_requests by payout_id and id desc order since payouts are ordered by id desc
        stripe_payout_requests.sort(
            key=lambda stripe_payout_request: (
                -stripe_payout_request.payout_id,
                -stripe_payout_request.id,
            )
        )
        stripe_payout_requests_count = len(stripe_payout_requests)
        instant_payouts = []

        # Find the latest stripe_payout_id for a payout, and form the response
        k = 0
        for i in range(payouts_count):
            stripe_payout_id = None
            for j in range(k, stripe_payout_requests_count):
                if stripe_payout_requests[j].payout_id == payouts[i].id:
                    stripe_payout_id = stripe_payout_requests[j].stripe_payout_id
                    k = j
                    break
            payout_item = PayoutStreamItem(
                payout_account_id=payouts[i].payment_account_id,
                payout_id=payouts[i].id,
                amount=payouts[i].amount,
                currency=payouts[i].currency.lower(),
                fee=payouts[i].fee,
                status=payouts[i].status,
                pgp_payout_id=stripe_payout_id,
                created_at=payouts[i].created_at.replace(tzinfo=pytz.utc),
            )
            instant_payouts.append(payout_item)

        new_offset: Optional[int] = None
        if len(payouts) >= self.request.limit:
            new_offset = self.request.offset + self.request.limit

        return GetPayoutStreamResponse(
            count=payouts_count, offset=new_offset, instant_payouts=instant_payouts
        )

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, GetPayoutStreamResponse]:
        raise
