from structlog.stdlib import BoundLogger
from typing import Optional, Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.cache.Cacheable import CacheKeyAware
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.payout.core.account import models as account_models
from app.payout.core.exceptions import payout_account_not_found_error
from app.payout.core.feature_flags import include_verification_requirements_get_account
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.models import PayoutAccountId


class GetPayoutAccountRequest(OperationRequest, CacheKeyAware):
    payout_account_id: PayoutAccountId

    def get_cache_key(self) -> dict:
        return {"payout_account_id": self.payout_account_id}


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
            self.logger.error(
                "[Payout Account] get_payment_account_by_id failed",
                extra={"payout_account_id": self.request.payout_account_id},
            )
            raise payout_account_not_found_error()

        stripe_managed_account: Optional[StripeManagedAccount] = None
        if payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )

        verification_requirements = None
        if stripe_managed_account and include_verification_requirements_get_account():
            verification_requirements = account_models.VerificationRequirements(
                verification_status=stripe_managed_account.verification_status,
                due_by=stripe_managed_account.verification_due_by,
                additional_error_info=stripe_managed_account.verification_error_info,
                required_fields_v1=stripe_managed_account.verification_fields_needed_v1,
                required_fields=stripe_managed_account.verification_fields_needed,
            )
        return account_models.PayoutAccountInternal(
            payment_account=payment_account,
            pgp_external_account_id=stripe_managed_account.stripe_id
            if stripe_managed_account
            else None,
            verification_requirements=verification_requirements,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
