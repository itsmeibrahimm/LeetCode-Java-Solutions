from datetime import datetime

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
    payout_account_not_found_error,
    payout_method_update_error,
)
from app.payout.repository.bankdb.model.payment_account_edit_history import (
    PaymentAccountEditHistoryCreate,
)
from app.payout.repository.bankdb.model.payout_method import (
    PayoutMethodMiscellaneousCreate,
)
from app.payout.repository.bankdb.payment_account_edit_history import (
    PaymentAccountEditHistoryRepositoryInterface,
)
from app.payout.repository.bankdb.payout_method_miscellaneous import (
    PayoutMethodMiscellaneousRepositoryInterface,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout import models


class CreatePayoutMethodRequest(OperationRequest):
    payout_account_id: models.PayoutAccountId
    token: models.PayoutMethodExternalAccountToken
    type: models.PayoutExternalAccountType


class CreatePayoutMethod(
    AsyncOperation[
        CreatePayoutMethodRequest,
        Union[
            account_models.PayoutCardInternal, account_models.PayoutBankAccountInternal
        ],
    ]
):
    """
    Processor to create a payout method
    """

    payment_account_repo: PaymentAccountRepositoryInterface
    payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface
    payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepositoryInterface
    stripe: StripeAsyncClient

    def __init__(
        self,
        request: CreatePayoutMethodRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        payment_account_edit_history_repo: PaymentAccountEditHistoryRepositoryInterface,
        payout_method_miscellaneous_repo: PayoutMethodMiscellaneousRepositoryInterface,
        logger: BoundLogger = None,
        stripe: StripeAsyncClient,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo
        self.payment_account_edit_history_repo = payment_account_edit_history_repo
        self.payout_method_miscellaneous_repo = payout_method_miscellaneous_repo
        self.stripe = stripe

    async def _execute(
        self
    ) -> Union[
        account_models.PayoutCardInternal, account_models.PayoutBankAccountInternal
    ]:
        payout_account = await self.payment_account_repo.get_payment_account_by_id(
            self.request.payout_account_id
        )
        if not payout_account:
            raise payout_account_not_found_error()

        stripe_managed_account = await get_stripe_managed_account_by_payout_account_id(
            payout_account_id=self.request.payout_account_id,
            payment_account_repository=self.payment_account_repo,
        )
        if not stripe_managed_account or not stripe_managed_account.stripe_id:
            # no payment gateway provider account for this account
            raise pgp_account_not_found_error()

        self.logger.info(
            "Creating a new external account.",
            type=self.request.type,
            token=self.request.token,
            payout_account_id=self.request.payout_account_id,
        )
        country = CountryCode(stripe_managed_account.country_shortname)
        stripe_account_id = stripe_managed_account.stripe_id
        # call stripe to create an external account
        try:
            external_account = await self.stripe.create_external_account(
                request=CreateExternalAccountRequest(
                    country=country,
                    type=self.request.type,
                    stripe_account_id=stripe_account_id,
                    external_account_token=self.request.token,
                )
            )
            self.logger.info(
                "A new external account has been added to stripe account for payout account.",
                type=self.request.type,
                token=self.request.token,
                payout_account_id=self.request.payout_account_id,
            )
        except StripeError:
            self.logger.error(
                "Failed to add a new external account on Stripe.",
                type=self.request.type,
                token=self.request.token,
                payout_account_id=self.request.payout_account_id,
            )
            # add more error handling, raise internal error for now
            raise payout_method_create_error()

        if not external_account:
            # Failed to create a stripe external account
            self.logger.error(
                "Failed to add a new external account for payout account.",
                payout_account_id=self.request.payout_account_id,
                card_token=self.request.token,
            )
            raise payout_method_create_error()

        if self.request.type == models.PayoutExternalAccountType.CARD:
            return await self._post_create_card(external_account)
        else:
            return await self._post_create_bank_account(
                stripe_managed_account, bank_account=external_account
            )

    def _handle_exception(
        self, dep_exec: BaseException
    ) -> Union[PaymentException, account_models.PayoutCardInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION

    async def _post_create_card(self, card) -> account_models.PayoutCardInternal:
        # mark the existing default payout_methods to non-default
        # create a default payout_method for the newly added card
        # create a payout_card object for the newly added card and newly created payout_method
        payout_method, payout_card = await self.payout_method_miscellaneous_repo.unset_default_and_create_payout_method_and_payout_card(
            PayoutMethodMiscellaneousCreate(
                payout_account_id=self.request.payout_account_id,
                payout_method_type=models.PayoutExternalAccountType.CARD.value,
                card=card,
            )
        )
        self.logger.info(
            "Created default payout_method for payout account.",
            token=self.request.token,
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

    async def _post_create_bank_account(
        self, stripe_managed_account, bank_account
    ) -> account_models.PayoutBankAccountInternal:
        # update the stripe_managed_account with the new bank info and update payment_account_edit_history
        old_bank_name = stripe_managed_account.default_bank_name
        old_bank_last4 = stripe_managed_account.default_bank_last_four
        old_fingerprint = stripe_managed_account.fingerprint
        stripe_managed_account = await self.payment_account_repo.update_stripe_managed_account_by_id(
            stripe_managed_account_id=stripe_managed_account.id,
            data=StripeManagedAccountUpdate(
                fingerprint=bank_account.fingerprint,
                default_bank_last_four=bank_account.last4,
                default_bank_name=bank_account.bank_name,
                stripe_last_updated_at=datetime.utcnow(),
            ),
        )
        if not stripe_managed_account:
            self.logger.error(
                "Added a new bank account, updating bank info on SMA failed.",
                stripe_managed_account_id=stripe_managed_account.id,
            )
            # SMA update failed, raise
            raise payout_method_update_error(
                "Failed to update SMA after stripe external account has been updated."
            )
        new_bank_name = stripe_managed_account.default_bank_name
        new_bank_last4 = stripe_managed_account.default_bank_last_four
        new_fingerprint = stripe_managed_account.fingerprint
        if old_fingerprint == new_fingerprint:
            self.logger.error(
                "Added a new bank account, the new bank info has not been updated on SMA.",
                stripe_managed_account_id=stripe_managed_account.id,
            )
            # SMA update failed, raise
            raise payout_method_update_error(
                "Failed to update SMA after stripe external account has been updated."
            )
        else:
            # Save a record to payment_account_edit_history table only if SMA has been updated
            # Since stripe_managed_account and payment_account_edit_history are not in the same database for now
            # so we can't do atomic update here
            # We should make update stripe_managed_account and payment_account_edit_history atomic after db migration
            payment_account_edit_history_record = await self.payment_account_edit_history_repo.record_bank_update(
                data=PaymentAccountEditHistoryCreate(
                    account_type=models.AccountType.ACCOUNT_TYPE_STRIPE_MANAGED_ACCOUNT,
                    account_id=stripe_managed_account.id,
                    new_bank_name=new_bank_name,
                    new_bank_last4=new_bank_last4,
                    new_fingerprint=new_fingerprint,
                    payment_account_id=self.request.payout_account_id,
                    owner_type=None,
                    owner_id=None,
                    old_bank_name=old_bank_name,
                    old_bank_last4=old_bank_last4,
                    old_fingerprint=old_fingerprint,
                    login_as_user_id=None,
                    user_id=None,
                    device_id=None,
                    ip=None,
                )
            )
            if payment_account_edit_history_record.new_fingerprint != new_fingerprint:
                self.logger.error(
                    "Added a new bank account, the new bank info has not been recorded in "
                    "PaymentAccountEditHistory.",
                    stripe_managed_account_id=stripe_managed_account.id,
                )

            return account_models.PayoutBankAccountInternal(
                payout_account_id=self.request.payout_account_id,
                currency=bank_account.currency,
                country=bank_account.country,
                bank_last4=new_bank_last4,
                bank_name=new_bank_name,
                fingerprint=new_fingerprint,
            )
