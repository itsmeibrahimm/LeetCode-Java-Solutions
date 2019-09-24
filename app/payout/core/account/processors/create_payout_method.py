from typing import Union

from stripe.error import StripeError

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.context.logger import Log
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import CreateExternalAccountRequest
from app.commons.types import CountryCode
from app.payout.core.account.types import PayoutCardInternal
from app.payout.core.account.utils import (
    get_stripe_managed_account_by_payout_account_id,
)
from app.payout.core.exceptions import (
    pgp_account_not_found_error,
    payout_method_create_error,
)
from app.payout.repository.bankdb.model.payout_method import (
    PayoutMethodMiscellaneousCreate,
)
from app.payout.repository.bankdb.payout_method_miscellaneous import (
    PayoutMethodMiscellaneousRepositoryInterface,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.types import (
    PayoutMethodExternalAccountToken,
    PayoutExternalAccountType,
    PayoutAccountId,
)


class CreatePayoutMethodRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    token: PayoutMethodExternalAccountToken
    type: PayoutExternalAccountType


class CreatePayoutMethod(AsyncOperation[CreatePayoutMethodRequest, PayoutCardInternal]):
    """
    Processor to create a payout method
    """

    payment_account_repo: PaymentAccountRepositoryInterface
    payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepositoryInterface
    stripe: StripeAsyncClient

    def __init__(
        self,
        request: CreatePayoutMethodRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepositoryInterface,
        logger: Log = None,
        stripe: StripeAsyncClient,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo
        self.payout_method_miscellaneous_repo = payout_method_miscellaneous_repo
        self.stripe = stripe

    async def _execute(self) -> PayoutCardInternal:
        stripe_managed_account = await get_stripe_managed_account_by_payout_account_id(
            payout_account_id=self.request.payout_account_id,
            payment_account_repository=self.payment_account_repo,
        )
        if not stripe_managed_account or not stripe_managed_account.stripe_id:
            # no payment gateway provider account for this account
            raise pgp_account_not_found_error()

        country = CountryCode(stripe_managed_account.country_shortname)
        stripe_account_id = stripe_managed_account.stripe_id
        # call stripe to create an external account
        try:
            card = await self.stripe.create_external_account_card(
                request=CreateExternalAccountRequest(
                    country=country,
                    type=self.request.type,
                    stripe_account_id=stripe_account_id,
                    external_account_token=self.request.token,
                )
            )
            self.logger.info(
                f"A debit card {card.id} has been added to stripe account {stripe_account_id} "
                f"for account {self.request.payout_account_id}"
            )
        except StripeError:
            self.logger.error(
                f"Error creating payout method {self.request.token} for account "
                f"{self.request.payout_account_id}"
            )
            # add more error handling, raise internal error for now
            raise payout_method_create_error()

        if not card:
            # Failed to create a stripe external account
            self.logger.error(
                f"Error creating payout method {self.request.token} for account "
                f"{self.request.payout_account_id}"
            )
            raise payout_method_create_error()

        # mark the existing default payout_methods to non-default
        # create a default payout_method for the newly added card
        # create a payout_card object for the newly added card and newly created payout_method
        payout_method, payout_card = await self.payout_method_miscellaneous_repo.unset_default_and_create_payout_method_and_payout_card(
            PayoutMethodMiscellaneousCreate(
                payout_account_id=self.request.payout_account_id,
                payout_method_type=PayoutExternalAccountType.CARD.value,
                card=card,
            )
        )
        self.logger.info(
            f"Created default payout_method {payout_method} and payout_card {payout_card} for stripe card {card.id}"
        )

        return PayoutCardInternal(
            stripe_card_id=payout_card.stripe_card_id,
            last4=payout_card.last4,
            brand=payout_card.brand,
            exp_month=payout_card.exp_month,
            exp_year=payout_card.exp_year,
            fingerprint=payout_card.fingerprint,
            payout_account_id=payout_method.payment_account_id,
            currency=payout_method.currency,
            country=payout_method.country,
            is_default=payout_method.is_default,
            id=payout_method.id,
            token=payout_method.token,
            created_at=payout_method.created_at,
            updated_at=payout_method.updated_at,
            deleted_at=payout_method.deleted_at,
        )

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, PayoutCardInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
