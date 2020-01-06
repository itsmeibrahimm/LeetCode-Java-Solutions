from datetime import datetime

from structlog.stdlib import BoundLogger
from typing import Union

from app.commons.api.models import DEFAULT_INTERNAL_EXCEPTION, PaymentException
from app.commons.cache.Cacheable import CacheKeyAware
from app.commons.core.processor import OperationRequest, AsyncOperation
from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.providers.stripe.stripe_models import (
    CreateAccountRequest,
    UpdateAccountRequest,
)
from app.commons.types import CountryCode
from app.payout.core.account import models
from app.payout.core.exceptions import (
    payout_account_not_found_error,
    pgp_account_create_invalid_request,
    pgp_account_create_error,
    pgp_account_update_error,
)
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccountCreateAndPaymentAccountUpdate,
    StripeManagedAccountUpdate,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.payout.models import PayoutAccountId, StripeAccountToken
import stripe.error as stripe_error


class VerifyPayoutAccountRequest(OperationRequest, CacheKeyAware):
    def get_cache_key(self) -> dict:
        return {"payout_account_id": self.payout_account_id}

    payout_account_id: PayoutAccountId
    country: CountryCode
    account_token: StripeAccountToken


class VerifyPayoutAccount(
    AsyncOperation[VerifyPayoutAccountRequest, models.PayoutAccountInternal]
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

    async def _execute(self) -> models.PayoutAccountInternal:
        # get payout account
        payment_account = await self.payment_account_repo.get_payment_account_by_id(
            self.request.payout_account_id
        )
        if not payment_account:
            self.logger.error(
                "[Account Verify] get_payment_account_by_id error",
                extra={"payout_account_id": self.request.payout_account_id},
            )
            raise payout_account_not_found_error()

        # get sma if payment_account.account_id is not null
        stripe_managed_account = None
        if payment_account.account_id:
            stripe_managed_account = await self.payment_account_repo.get_stripe_managed_account_by_id(
                payment_account.account_id
            )

        # create new stripe account if no sma
        if not stripe_managed_account:
            # create stripe account
            self.logger.info(
                "[Account Verify] creating stripe account",
                extra={"payment_account_id": payment_account.id},
            )
            create_account = CreateAccountRequest(
                country=self.request.country, account_token=self.request.account_token
            )
            # call stripe to create an account
            try:
                stripe_account = await self.stripe_client.create_account(
                    request=create_account
                )
            except stripe_error.InvalidRequestError as e:
                error_info = e.json_body.get("error", {})
                stripe_error_message = error_info.get("message")
                self.logger.error(
                    "[Account Verify] create stripe account failed due to invalid request error",
                    extra={
                        "payment_account_id": payment_account.id,
                        "account_token": self.request.account_token,
                        "error": stripe_error_message,
                    },
                )
                raise pgp_account_create_invalid_request(
                    error_message=stripe_error_message
                )
            except stripe_error.StripeError as e:
                error_info = e.json_body.get("error", {})
                stripe_error_message = error_info.get("message")
                self.logger.error(
                    "[Account Verify] create stripe account error",
                    extra={
                        "payment_account_id": payment_account.id,
                        "account_token": self.request.account_token,
                        "error": stripe_error_message,
                    },
                )
                raise pgp_account_create_error(stripe_error_message)
            except Exception:
                self.logger.error(
                    "[Account Verify] create stripe account failed due to other error",
                    extra={
                        "payment_account_id": payment_account.id,
                        "account_token": self.request.account_token,
                    },
                )
                raise pgp_account_create_error()

            # create stripe_managed_account and update the linked payment_account
            stripe_managed_account, payment_account = await self.payment_account_repo.create_stripe_managed_account_and_update_payment_account(
                data=StripeManagedAccountCreateAndPaymentAccountUpdate(
                    stripe_id=stripe_account.id,
                    country_shortname=self.request.country.value,
                    payment_account_id=payment_account.id,
                )
            )
            self.logger.info(
                "[Account Verify] create stripe account, sma and update payment_account succeed",
                extra={
                    "payment_account_id": payment_account.id,
                    "stripe_account_id": stripe_account.id,
                    "country": self.request.country.value,
                },
            )
        else:
            # update stripe account
            self.logger.info(
                "[Account Verify] updating stripe account",
                extra={"payment_account_id": payment_account.id},
            )
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
                self.logger.error(
                    "[Account Verify] updating stripe account error",
                    extra={
                        "payment_account_id": payment_account.id,
                        "account_token": self.request.account_token,
                        "error": stripe_error_message,
                    },
                )
                raise pgp_account_update_error(stripe_error_message)
            except Exception:
                self.logger.error(
                    "[Account Verify] update stripe account failed due to other error",
                    extra={
                        "payment_account_id": payment_account.id,
                        "account_token": self.request.account_token,
                    },
                )
                raise pgp_account_update_error()

            # update sma
            await self.payment_account_repo.update_stripe_managed_account_by_id(
                stripe_managed_account_id=stripe_managed_account.id,
                data=StripeManagedAccountUpdate(
                    stripe_last_updated_at=datetime.utcnow()
                ),
            )
            self.logger.info(
                "[Account Verify] updating stripe account and sma succeed",
                extra={"payment_account_id": payment_account.id},
            )

        return models.PayoutAccountInternal(
            payment_account=payment_account, pgp_external_account_id=stripe_account.id
        )

    def _handle_exception(
        self, internal_exec: BaseException
    ) -> Union[PaymentException, models.PayoutAccountInternal]:
        raise DEFAULT_INTERNAL_EXCEPTION
