import json
from typing import Union

from structlog import BoundLogger

from app.commons.core.errors import (
    PaymentError,
    PGPConnectionError,
    PGPApiError,
    PGPRateLimitError,
)
from app.commons.core.processor import AsyncOperation
from app.commons.providers.stripe.constants import STRIPE_PLATFORM_ACCOUNT_IDS
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import StripeCreateTransferRequest
from app.commons.types import CountryCode
from app.payout.core.instant_payout.models import (
    SMATransferRequest,
    SMATransferResponse,
    InstantPayoutSMATransferDefaultDescription,
    InstantPayoutDefaultMetaData,
    InstantPayoutStatusType,
)
from app.payout.repository.bankdb.model.payout import PayoutUpdate
from app.payout.repository.bankdb.model.stripe_managed_account_transfer import (
    StripeManagedAccountTransferCreate,
)
from app.payout.repository.bankdb.payout import PayoutRepositoryInterface
from app.payout.repository.bankdb.stripe_managed_account_transfer import (
    StripeManagedAccountTransferRepository,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface


class SubmitSMATransfer(AsyncOperation[SMATransferRequest, SMATransferResponse]):
    """Create and Submit Stripe Transfer.

    Submit Stripe Transfer from Platform account to connected account.
    """

    def __init__(
        self,
        request: SMATransferRequest,
        stripe_managed_account_transfer_repo: StripeManagedAccountTransferRepository,
        stripe_client: StripeAsyncClient,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_managed_account_transfer_repo = stripe_managed_account_transfer_repo
        self.payout_repo = payout_repo
        self.transaction_repo = transaction_repo
        self.stripe_client = stripe_client
        self.logger = logger

    async def _execute(self) -> SMATransferResponse:
        self.logger.info(
            "[Instant Payout Submit]: Submitting SMA transfer",
            request=self.request.dict(),
        )
        # Create StripeManagedAccountTransfer record
        data = StripeManagedAccountTransferCreate(
            amount=self.request.amount,
            from_stripe_account_id=STRIPE_PLATFORM_ACCOUNT_IDS[
                CountryCode(self.request.country.upper())
            ],
            to_stripe_account_id=self.request.destination,
            token=self.request.idempotency_key,
        )
        await (
            self.stripe_managed_account_transfer_repo.create_stripe_managed_account_transfer(
                data=data
            )
        )
        # Submit SMA Transfer to Stripe
        stripe_create_transfer_request = StripeCreateTransferRequest(
            description=InstantPayoutSMATransferDefaultDescription,
            metadata=InstantPayoutDefaultMetaData,
            idempotency_key=self.request.idempotency_key,
        )
        try:
            stripe_transfer = await self.stripe_client.create_transfer_with_stripe_error_translation(
                country=self.request.country,
                currency=self.request.currency,
                destination=self.request.destination,
                amount=self.request.amount,
                request=stripe_create_transfer_request,
            )
        except (PGPConnectionError, PGPApiError, PGPRateLimitError) as e:
            # Handle PGPConnectionError, PGPApiError and mark payout as error to avoid daily limit
            # And detach transactions
            self.logger.info(
                "[Instant Payout Submit]: fail to submit SMA transfer due to PGPError, detaching transactions",
                request=self.request.dict(),
                error=str(e),
            )
            payout_update = PayoutUpdate(
                status=InstantPayoutStatusType.ERROR, error=json.dumps(e.__dict__)
            )
            await self.payout_repo.update_payout_by_id(
                payout_id=self.request.payout_id, data=payout_update
            )
            await self.transaction_repo.set_transaction_payout_id_by_ids(
                transaction_ids=self.request.transaction_ids, payout_id=None
            )
            raise

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
        # Need to detach transactions when bad things happened
        raise
