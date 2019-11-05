from typing import Optional

from starlette.status import HTTP_400_BAD_REQUEST

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.commons.types import CountryCode
from app.payout.core.exceptions import PayoutError, PayoutErrorCode
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.commons.providers.stripe import stripe_models as models
from app.payout.models import PayoutAccountId

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
