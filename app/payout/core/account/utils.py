from typing import Optional

from app.commons.providers.stripe.stripe_client import StripeAsyncClient
from app.payout.repository.maindb.model.payment_account import PaymentAccount
from app.payout.repository.maindb.model.stripe_managed_account import (
    StripeManagedAccount,
)
from app.payout.repository.maindb.payment_account import (
    PaymentAccountRepositoryInterface,
)
from app.commons.providers.stripe import stripe_models as models


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


async def get_account_balance(
    stripe_managed_account: Optional[StripeManagedAccount], stripe: StripeAsyncClient
) -> int:
    """
    Get balance for stripe account, return 0 if sma is not created
    :param stripe_managed_account: stripe managed account
    :param stripe: StripeClient
    :return: balance amount
    """
    if stripe_managed_account:
        balance = await stripe.retrieve_balance(
            stripe_account=models.StripeAccountId(stripe_managed_account.stripe_id),
            country=models.CountryCode(stripe_managed_account.country_shortname),
        )
        try:
            return balance.available[0].amount
        except KeyError:
            return 0
    return 0
