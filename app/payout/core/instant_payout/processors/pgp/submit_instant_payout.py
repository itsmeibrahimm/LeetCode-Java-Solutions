from typing import Union

from structlog import BoundLogger

from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import StripeCreatePayoutRequest
from app.payout.core.instant_payout.models import (
    SubmitInstantPayoutRequest,
    SubmitInstantPayoutResponse,
    InstantPayoutDefaultMetaData,
    InstantPayoutDefaultDescription,
    InstantPayoutDefaultMethod,
    InstantPayoutDefaultStatementDescriptor,
)


class SubmitInstantPayout(
    AsyncOperation[SubmitInstantPayoutRequest, SubmitInstantPayoutResponse]
):
    """Submit Instant Payout.

    Submit Instant payout to Connected Account's debit card.
    """

    def __init__(
        self,
        request: SubmitInstantPayoutRequest,
        stripe_client: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_client = stripe_client
        self.logger = logger

    async def _execute(self) -> SubmitInstantPayoutResponse:
        stripe_create_payout_request = StripeCreatePayoutRequest(
            description=InstantPayoutDefaultDescription,
            destination=self.request.destination,
            metadata=InstantPayoutDefaultMetaData,
            method=InstantPayoutDefaultMethod,
            statement_descriptor=InstantPayoutDefaultStatementDescriptor,
            idempotency_key=self.request.idempotency_key,
        )
        stripe_payout = await self.stripe_client.create_payout(
            country=self.request.country,
            currency=self.request.currency,
            amount=self.request.amount,
            stripe_account=self.request.stripe_account_id,
            request=stripe_create_payout_request,
        )

        return SubmitInstantPayoutResponse(
            stripe_payout_id=stripe_payout.id,
            stripe_object=stripe_payout.object,
            status=stripe_payout.status,
            amount=stripe_payout.amount,
            currency=stripe_payout.currency,
            destination=stripe_payout.destination,
        )

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, SubmitInstantPayoutResponse]:
        raise
