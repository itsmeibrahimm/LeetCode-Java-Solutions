from typing import Dict

from app.commons.providers.stripe.types import StripePlatformAccountId
from app.commons.types import CountryCode


# These platform account ids are the same across both live and test, so they don't need to be configurable
STRIPE_PLATFORM_ACCOUNT_IDS: Dict[CountryCode, StripePlatformAccountId] = {
    CountryCode.CA: StripePlatformAccountId("acct_16qVpAAFJYNIHuof"),
    CountryCode.US: StripePlatformAccountId("acct_1xmerw8hWoEwIJg23PRk"),
    CountryCode.AU: StripePlatformAccountId("acct_1EVmnIBKMMeR8JVH"),
}
