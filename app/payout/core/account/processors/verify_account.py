from structlog.stdlib import BoundLogger
from typing import Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    CreateAccountRequest,
    UpdateAccountRequest,
)
from app.commons.types import CountryCode
from app.payout.core.account.types import PayoutAccountInternal
from app.payout.core.exceptions import (
    payout_account_not_found_error,
    pgp_account_create_invalid_request,
    pgp_account_create_error,
    pgp_account_update_error,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreateAndPaymentAccountUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.types import PayoutAccountId, StripeAccountToken
import stripe.error as stripe_error


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
    stripe_client: StripeAsyncClient

    def __init__(
        self,
        request: VerifyPayoutAccountRequest,
        *,
        payment_account_repo: PaymentAccountRepositoryInterface,
        logger: BoundLogger = None,
        stripe_client: StripeAsyncClient,
    ):
        super().__init__(request, logger)
        self.request = request
        self.payment_account_repo = payment_account_repo
        self.stripe_client = stripe_client

    async def _execute(self) -> PayoutAccountInternal:
        # get payout account
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            self.request.payout_account_id
        )
        if not payment_account:
            raise payout_account_not_found_error()

        # get sma if payment_account.account_id is not null
        stripe_managed_account = None
        if payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )
            self.logger.info(
                f"account_id {payment_account.account_id} exists for payout account "
                f"{payment_account.id} but no sma or stripe account exists"
            )

        # create new stripe account if no sma
        if not stripe_managed_account:
            # create stripe account
            create_account = CreateAccountRequest(
                country=self.request.country, account_token=self.request.account_token
            )
            # add more error handling
            try:
                stripe_account = await self.stripe_client.create_account(
                    request=create_account
                )
            # TODO: more comprehensive error handling in PAY-3793
            except stripe_error.InvalidRequestError as e:
                # raise BAD_REQUEST_ERROR
                error_info = e.json_body.get("error", {})
                stripe_error_message = error_info.get("message")
                raise pgp_account_create_invalid_request(
                    error_message=stripe_error_message
                )
            except stripe_error.StripeError as e:
                error_info = e.json_body.get("error", {})
                stripe_error_message = error_info.get("message")
                raise pgp_account_create_error(stripe_error_message)
            except Exception:
                raise pgp_account_create_error()

            # create stripe_managed_account and update the linked payment_account
            stripe_managed_account, payment_account = await self.payment_account_repo.create_stripe_managed_account_and_update_payment_account(
                data=StripeManagedAccountCreateAndPaymentAccountUpdate(
                    stripe_id=stripe_account.id,
                    country_shortname=self.request.country.value,
                    payment_account_id=payment_account.id,
                )
            )
        else:
            # update stripe account
            update_account = UpdateAccountRequest(
                id=stripe_managed_account.stripe_id,
                country=self.request.country,
                account_token=self.request.account_token,
            )
            try:
                stripe_account = await self.stripe_client.update_account(
                    request=update_account
                )
            except stripe_error.StripeError as e:
                error_info = e.json_body.get("error", {})
                stripe_error_message = error_info.get("message")
                raise pgp_account_update_error(stripe_error_message)
            assert (
                stripe_account.id == stripe_managed_account.stripe_id
            ), "Updated stripe account id should be the same as the old one"

        return PayoutAccountInternal(
            payment_account=payment_account, pgp_external_account_id=stripe_account.id
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
