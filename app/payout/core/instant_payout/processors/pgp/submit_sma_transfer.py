from typing import Union

from structlog import BoundLogger

from app.commons.core.errors import PaymentError
from app.commons.core.processor import AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import StripeCreateTransferRequest
from app.payout.core.instant_payout.models import (
    SMATransferRequest,
    SMATransferResponse,
    InstantPayoutSMATransferDefaultDescription,
    InstantPayoutDefaultMetaData,
)


class SubmitSMATransfer(AsyncOperation[SMATransferRequest, SMATransferResponse]):
    """Submit Stripe Transfer.

    Submit Stripe Transfer from Platform account to connected account.
    """

    def __init__(
        self,
        request: SMATransferRequest,
        stripe_client: StripeAsyncClient,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_client = stripe_client
        self.logger = logger

    async def _execute(self) -> SMATransferResponse:
        stripe_create_transfer_request = StripeCreateTransferRequest(
            description=InstantPayoutSMATransferDefaultDescription,
            metadata=InstantPayoutDefaultMetaData,
            idempotency_key=self.request.idempotency_key,
        )
        stripe_transfer = await self.stripe_client.create_transfer(
            country=self.request.country,
            currency=self.request.currency,
            destination=self.request.destination,
            amount=self.request.amount,
            request=stripe_create_transfer_request,
        )
        return SMATransferResponse(
            stripe_transfer_id=stripe_transfer.id,
            stripe_object=stripe_transfer.object,
            amount=stripe_transfer.amount,
            currency=stripe_transfer.currency,
            destination=stripe_transfer.destination,
        )

    def _handle_exception(
        self, internal_exec: Exception
    ) -> Union[PaymentError, SMATransferResponse]:
        raise
