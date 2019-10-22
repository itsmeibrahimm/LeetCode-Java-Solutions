from structlog.stdlib import BoundLogger
from typing import Union

from stripe.error import StripeError

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import AsyncOperation, OperationRequest
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import CreateExternalAccountRequest
from app.commons.types import CountryCode
from app.payout.core.account import models as account_models
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
from app.payout.models import (
    PayoutMethodExternalAccountToken,
    PayoutExternalAccountType,
    PayoutAccountId,
)


class CreatePayoutMethodRequest(OperationRequest):
    payout_account_id: PayoutAccountId
    token: PayoutMethodExternalAccountToken
    type: PayoutExternalAccountType


class CreatePayoutMethod(
    AsyncOperation[CreatePayoutMethodRequest, account_models.PayoutCardInternal]
):
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
        logger: BoundLogger = None,
        stripe: StripeAsyncClient,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo
        self.payout_method_miscellaneous_repo = payout_method_miscellaneous_repo
        self.stripe = stripe

    async def _execute(self) -> account_models.PayoutCardInternal:
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
                "A debit card has been added to stripe account for payout account.",
                card_id=card.id,
                stripe_account_id=stripe_account_id,
                payout_account_id=self.request.payout_account_id,
            )
        except StripeError:
            self.logger.error(
                "Error creating payout method for payout account.",
                token=self.request.token,
                payout_account_id=self.request.payout_account_id,
            )
            # add more error handling, raise internal error for now
            raise payout_method_create_error()

        if not card:
            # Failed to create a stripe external account
            self.logger.error(
                "Error creating payout method for payout account.",
                token=self.request.token,
                payout_account_id=self.request.payout_account_id,
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
            f"Created default payout_method for payout account.",
            token=self.request.token,
            card_id=card.id,
            payout_account_id=self.request.payout_account_id,
        )

        return account_models.PayoutCardInternal(
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
    ) -> Union[PaymentException, account_models.PayoutCardInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
