from typing import Union

from IPython.utils.tz import utcnow

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.context.logger import Log
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import CreateAccountRequest
from app.commons.types import CountryCode
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.core.exceptions import payout_account_not_found_error
from app.payout.repository.maindb.model.payment_account import PaymentAccountUpdate
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.types import PayoutAccountId, StripeAccountToken, AccountType


class VerifyPayoutAccountRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    country: CountryCode
    account_token: StripeAccountToken


class VerifyPayoutAccount(
    AsyncOperation[VerifyPayoutAccountRequest, PayoutAccountInternal]
):
    """
    Processor to verify a payout account
    """

    payment_account_repo: PaymentAccountRepositoryInterface
    stripe: StripeAsyncClient

    def __init__(
        self,
        request: VerifyPayoutAccountRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        logger: Log = None,
        stripe: StripeAsyncClient
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo
        self.stripe = stripe

    async def _execute(self) -> PayoutAccountInternal:
        # get payout account
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            self.request.payout_account_id
        )
        if not payment_account:
            raise payout_account_not_found_error()

        # create stripe account
        create_account = CreateAccountRequest(
            country=self.request.country,
            type="custom",
            account_token=self.request.account_token,
            requested_capabilities=["legacy_payments"],
        )
        stripe_account = await self.stripe.create_stripe_account(request=create_account)

        if stripe_account:
            # create sma
            stripe_managed_account = await self.payment_account_repo.create_stripe_managed_account(
                data=StripeManagedAccountCreate(
                    stripe_id=stripe_account.id,
                    country_shortname=self.request.country.value,
                    stripe_last_updated_at=utcnow(),
                )
            )
            # update the linked payout_account
            if stripe_managed_account:
                payment_account = await self.payment_account_repo.update_payment_account_by_id(
                    payment_account_id=self.request.payout_account_id,
                    data=PaymentAccountUpdate(
                        account_id=stripe_managed_account.id,
                        account_type=AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
                    ),
                )
        return PayoutAccountInternal(
            payment_account=payment_account,
            pgp_external_account_id=stripe_account.id if stripe_account else None,
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
