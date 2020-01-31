import json
from datetime import datetime
from typing import Union

import pytz
from structlog import BoundLogger

from app.commons.core.errors import (
    PaymentError,
    PGPConnectionError,
    PGPApiError,
    PGPRateLimitError,
)
from app.commons.core.processor import AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import StripeCreatePayoutRequest
from app.payout.core.errors import (
    InstantPayoutCardDeclineError,
    InstantPayoutInsufficientFundError,
)
from app.payout.core.instant_payout.models import (
    SubmitInstantPayoutRequest,
    SubmitInstantPayoutResponse,
    InstantPayoutDefaultMetaData,
    InstantPayoutDefaultDescription,
    InstantPayoutDefaultMethod,
    InstantPayoutDefaultStatementDescriptor,
    InstantPayoutStatusType,
)
from app.payout.repository.bankdb.model.payout import PayoutUpdate
from app.payout.repository.bankdb.model.stripe_payout_request import (
    StripePayoutRequestCreate,
    StripePayoutRequestUpdate,
)
from app.payout.repository.bankdb.payout import PayoutRepositoryInterface
from app.payout.repository.bankdb.stripe_payout_request import (
    StripePayoutRequestRepositoryInterface,
)
from app.payout.repository.bankdb.transaction import TransactionRepositoryInterface


class SubmitInstantPayout(
    AsyncOperation[SubmitInstantPayoutRequest, SubmitInstantPayoutResponse]
):
    """Submit Instant Payout.

    Create StripePayoutRequest record and submit Instant Payout to Connected Account's debit card.


    """

    def __init__(
        self,
        request: SubmitInstantPayoutRequest,
        stripe_client: StripeAsyncClient,
        stripe_payout_request_repo: StripePayoutRequestRepositoryInterface,
        payout_repo: PayoutRepositoryInterface,
        transaction_repo: TransactionRepositoryInterface,
        logger: BoundLogger = None,
    ):
        super().__init__(request, logger)
        self.request = request
        self.stripe_payout_request_repo = stripe_payout_request_repo
        self.payout_repo = payout_repo
        self.transaction_repo = transaction_repo
        self.stripe_client = stripe_client
        self.logger = logger

    async def _execute(self) -> SubmitInstantPayoutResponse:
        self.logger.info(
            "[Instant Payout Submit]: Submitting Instant Payout",
            request=self.request.dict(),
        )

        # Create StripePayoutRequest record
        request_field = {
            "country": self.request.country,
            "stripe_account_id": self.request.stripe_account_id,
            "amount": self.request.amount,
            "method": InstantPayoutDefaultMethod,
            "external_account_id": self.request.destination,
            "statement_descriptor": InstantPayoutDefaultStatementDescriptor,
            "idempotency_key": "instant-payout-{}".format(self.request.idempotency_key),
        }
        data = StripePayoutRequestCreate(
            payout_id=self.request.payout_id,
            idempotency_key="{}-request".format(self.request.idempotency_key),
            payout_method_id=self.request.payout_method_id,
            request=json.dumps(request_field),
            status=InstantPayoutStatusType.NEW,
            stripe_account_id=self.request.stripe_account_id,
        )
        stripe_payout_request = await self.stripe_payout_request_repo.create_stripe_payout_request(
            data=data
        )

        stripe_create_payout_request = StripeCreatePayoutRequest(
            description=InstantPayoutDefaultDescription,
            destination=self.request.destination,
            metadata=InstantPayoutDefaultMetaData,
            method=InstantPayoutDefaultMethod,
            statement_descriptor=InstantPayoutDefaultStatementDescriptor,
            # use idempotency_key from request_field to be consistent with the key in DSJ
            idempotency_key=request_field["idempotency_key"],
        )

        utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)
        status_to_update = None
        stripe_payout_id = None
        response = None
        error = None
        received_at = None
        try:
            stripe_payout = await self.stripe_client.create_payout_with_stripe_error_translation(
                country=self.request.country,
                currency=self.request.currency,
                amount=self.request.amount,
                stripe_account=self.request.stripe_account_id,
                request=stripe_create_payout_request,
            )
            status_to_update = stripe_payout.status
            stripe_payout_id = stripe_payout.id
            response = str(stripe_payout)
        except (
            PGPConnectionError,
            PGPApiError,
            PGPRateLimitError,
            InstantPayoutInsufficientFundError,
        ) as e:
            # Handle PGPConnectionError, PGPApiError, PGPRateLimitError and mark payout as *error* and detach
            # transactions to avoid daily limit
            # Also handle InstantPayoutInsufficientFundError here, since it's because of stripe's funding lag (DD
            # platform account to connected account). Should mark payout as error to let client retry
            self.logger.warn(
                "[Instant Payout Submit]: fail to submit Instant Payout due to PGP issue, detaching transactions",
                request=self.request.dict(),
            )
            status_to_update = InstantPayoutStatusType.ERROR
            error = json.dumps(e.__dict__)
            received_at = utc_now
            await self.transaction_repo.set_transaction_payout_id_by_ids(
                transaction_ids=self.request.transaction_ids, payout_id=None
            )
            raise
        except InstantPayoutCardDeclineError as e:
            # Handle InstantPayoutCardDeclineError, and mark payout status as failed to limit retry
            # And detach transactions
            self.logger.warn(
                "[Instant Payout Submit]: fail to submit Instant Payout due to card decline, detaching transactions",
                request=self.request.dict(),
            )
            status_to_update = InstantPayoutStatusType.FAILED
            error = json.dumps(e.__dict__)
            received_at = utc_now
            await self.transaction_repo.set_transaction_payout_id_by_ids(
                transaction_ids=self.request.transaction_ids, payout_id=None
            )
            raise
        finally:
            await self.payout_repo.update_payout_by_id(
                payout_id=self.request.payout_id,
                data=PayoutUpdate(status=status_to_update, error=error),
            )
            await self.stripe_payout_request_repo.update_stripe_payout_request_by_id(
                stripe_payout_request_id=stripe_payout_request.id,
                data=StripePayoutRequestUpdate(
                    status=status_to_update,
                    stripe_payout_id=stripe_payout_id,
                    response=response,
                    received_at=received_at,
                ),
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
