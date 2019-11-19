import json

from structlog.stdlib import BoundLogger
from typing import Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.errors import DatabaseError
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import RetrieveAccountRequest
from app.payout.core.account import models as account_models
from app.payout.core.account.utils import get_verification_requirements_from_stripe_obj
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)


class GetVerificationRequirementsRequest(OperationRequest):
    stripe_managed_account_id: int
    country_shortname: str
    stripe_id: str


class GetVerificationRequirements(
    AsyncOperation[
        GetVerificationRequirementsRequest, account_models.VerificationRequirements
    ]
):
    """
    Processor to get verification requirements from stripe for a payout account
    """

    payment_account_repo: PaymentAccountRepositoryInterface

    def __init__(
        self,
        request: GetVerificationRequirementsRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        stripe_client: StripeAsyncClient,
        logger: BoundLogger = None
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo
        self.stripe_client = stripe_client

    async def _execute(self) -> account_models.VerificationRequirements:
        stripe_managed_account_id = self.request.stripe_managed_account_id
        stripe_id = self.request.stripe_id
        country_shortname = self.request.country_shortname

        try:
            retrieve_stripe_account_request = RetrieveAccountRequest(
                country=country_shortname, account_id=stripe_id
            )
            retrieved_stripe_account = await self.stripe_client.retrieve_stripe_account(
                retrieve_stripe_account_request
            )
            assert retrieved_stripe_account, "stripe call returned"
            verification_requirements = get_verification_requirements_from_stripe_obj(
                retrieved_stripe_account
            )

            # Updating in DB
            try:
                await self.payment_account_repo.update_stripe_managed_account_by_id(
                    stripe_managed_account_id=stripe_managed_account_id,
                    data=StripeManagedAccountUpdate(
                        verification_due_by=verification_requirements.due_by,
                        verification_fields_needed_v1=json.dumps(
                            verification_requirements.required_fields_v1.dict()
                        ),
                        verification_status=verification_requirements.verification_status,
                        verification_error_info=verification_requirements.additional_error_info,
                        # some new fields, but still backward compatible
                    ),
                )
            except DatabaseError as e:
                self.logger.warning(
                    "[GetVerificationRequirements] Error while updating verification information on SMA",
                    verification_required=verification_requirements,
                    stripe_managed_account_id=stripe_managed_account_id,
                    error=e,
                )

            return verification_requirements

        except Exception as e:
            # Catching all Exceptions because no matter what type of exception,
            # we do not want exception in Stripe fetch to break the flow
            # Making sure non-critical flow doesn't break the retrieval
            self.logger.warning(
                "[GetVerificationRequirements] Exception while fetching Account object from PGP/Stripe",
                stripe_id=stripe_id,
                country_shortname=country_shortname,
                stripe_managed_account_id=stripe_managed_account_id,
                error=e,
            )
            return account_models.VerificationRequirements()

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.VerificationRequirements]:
        raise DEFAULT_INTERNAL_EXCEPTION
