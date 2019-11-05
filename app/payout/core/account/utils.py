from typing import Optional

from starlette.status import HTTP_400_BAD_REQUEST
from structlog import BoundLogger, get_logger

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.types import CountryCode
import app.payout.core.account.models as account_model
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.models import PayoutAccountId, StripeBusinessType
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.commons.providers.stripe import stripe_models as models

COUNTRY_TO_CURRENCY_CODE = {
    "US": "USD",
    "CA": "CAD",
    "United States": "USD",
    "Canada": "CAD",
    "Indonesia": "IDR",
    "ID": "IDR",
    "SG": "SGD",
    "MY": "MYR",
    "JP": "JPY",
    "AU": "AUD",
}

logger: BoundLogger = get_logger()


async def get_country_shortname(
    payment_account: Optional[PaymentAccount],
    payment_account_repository: PaymentAccountRepositoryInterface,
) -> Optional[str]:
    if payment_account and payment_account.account_id:
        stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
            payment_account.account_id
        )
        if stripe_managed_account:
            return stripe_managed_account.country_shortname
    return None


async def get_country_by_payout_account_id(
    payout_account_id: PayoutAccountId,
    payment_account_repository: PaymentAccountRepositoryInterface,
) -> Optional[CountryCode]:
    payment_account = await payment_account_repository.get_payment_account_by_id(
        payout_account_id
    )
    if payment_account and payment_account.account_id:
        stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
            payment_account.account_id
        )
        if stripe_managed_account:
            return CountryCode(stripe_managed_account.country_shortname)
    return None


async def get_stripe_managed_account_by_payout_account_id(
    payout_account_id: PayoutAccountId,
    payment_account_repository: PaymentAccountRepositoryInterface,
) -> Optional[StripeManagedAccount]:
    payment_account = await payment_account_repository.get_payment_account_by_id(
        payout_account_id
    )
    if payment_account and payment_account.account_id:
        stripe_managed_account = await payment_account_repository.get_stripe_managed_account_by_id(
            payment_account.account_id
        )
        return stripe_managed_account
    return None


def get_currency_code(country_shortname: str) -> str:
    """
    Shortname country code in 2-letter ISO format.  Return none if not valid country.
    """
    if country_shortname in COUNTRY_TO_CURRENCY_CODE:
        return COUNTRY_TO_CURRENCY_CODE[country_shortname]
    raise PayoutError(
        http_status_code=HTTP_400_BAD_REQUEST,
        error_code=PayoutErrorCode.UNSUPPORTED_COUNTRY,
        retryable=False,
    )


async def get_account_balance(
    stripe_managed_account: Optional[StripeManagedAccount], stripe: StripeAsyncClient
) -> int:
    """
    Get balance for stripe account, return 0 if sma is not created
    :param stripe_managed_account: stripe managed account
    :param stripe: StripeAsyncClient
    :return: balance amount
    """
    if stripe_managed_account:
        balance = await stripe.retrieve_balance(
            stripe_account=models.StripeAccountId(stripe_managed_account.stripe_id),
            country=models.CountryCode(stripe_managed_account.country_shortname),
        )
        try:
            return balance.available[0].amount
        except AttributeError:
            return 0
    return 0


def get_internal_verification_status(
    stripe_response: models.Account = None
) -> Optional[account_model.VerificationStatus]:
    # company.verification is not sent in the Account payload. So considering document verification status only for individuals
    # BLOCKED : If either charges or payouts are blocked for the account - details will be specified in additional_error_info
    # FIELDS_REQUIRED : If there's any field in past_due, currently_due, eventually_due
    # PENDING : If there's any field in pending_verification
    # VERIFIED : If no fields in any of the lists and for Individual, also checks for
    # For all None cases, the calling method can handle by keeping the existing status
    try:
        stripe_status_entity = None
        if stripe_response:
            try:
                # If Business type is None, it'll be listed as a requirement, so will be handled by the rest of the code
                if (
                    stripe_response.business_type
                    and stripe_response.business_type == StripeBusinessType.INDIVIDUAL
                    and stripe_response.individual
                ):
                    stripe_status_entity = (
                        stripe_response.individual.verification.status
                        if stripe_response.individual.verification
                        else None
                    )
            except AttributeError as e:
                # When the entity is COMPANY, this attribute (individual) does not exist and may throw an exception
                logger.info(
                    "[AttributeError] in get_internal_verification_status - {}".format(
                        e
                    )
                )
            # Status to BLOCKED
            if not (
                stripe_response.payouts_enabled and stripe_response.charges_enabled
            ):
                return (
                    account_model.VerificationStatus.BLOCKED
                )  # Error info should contain info about what is disabled - charges or payouts
            if stripe_response.requirements:
                has_past_due: bool = len(
                    stripe_response.requirements["past_due"]
                ) > 0 if stripe_response.requirements["past_due"] else False
                has_currently_due: bool = len(
                    stripe_response.requirements["currently_due"]
                ) > 0 if stripe_response.requirements["currently_due"] else False
                has_eventually_due: bool = len(
                    stripe_response.requirements["eventually_due"]
                ) > 0 if stripe_response.requirements["eventually_due"] else False
                fields_needed: bool = has_past_due or has_currently_due or has_eventually_due
                # Status to FIELDS_REQUIRED
                if fields_needed:
                    return account_model.VerificationStatus.FIELDS_REQUIRED
                is_verification_pending: bool = len(
                    stripe_response.requirements["pending_verification"]
                ) > 0 if stripe_response.requirements["pending_verification"] else False
                # Status to PENDING
                if is_verification_pending or (
                    (stripe_status_entity and stripe_status_entity.lower() == "pending")
                ):
                    return account_model.VerificationStatus.PENDING
                # Status to VERIFIED
                if (
                    (
                        stripe_status_entity
                        and stripe_status_entity.lower() == "verified"
                    )
                    or (
                        stripe_response.business_type
                        and stripe_response.business_type == StripeBusinessType.COMPANY
                    )
                ) and not (fields_needed or is_verification_pending):
                    return account_model.VerificationStatus.VERIFIED
    except KeyError as e:
        logger.info("[KeyError] in get_internal_verification_status - {}".format(e))
    return None
