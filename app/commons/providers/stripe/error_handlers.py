import asyncio
from functools import wraps
import stripe.error as stripe_error

from app.commons.core.errors import PGPApiError, PGPConnectionError, PGPRateLimitError
from app.commons.providers.stripe.errors import (
    StripeErrorParser,
    StripeErrorCode,
    StripeErrorType,
)


def translate_stripe_error(func):
    """Translate Stripe Errors into payment processor layer errors.

    This function maps stripe errors into corresponding payment errors, so that the processor and above layers does not
    need to know the downstream error details. So that it is easy to support multiple providers or swap stripe with
    other providers.

    We should only handle know errors. For unknown errors, should let it bubble up.

    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(func):
            raise Exception(
                "translate_stripe_error decorator can't not used in async function."
            )
        try:
            result = func(*args, **kwargs)
            return result
        # Handle APIConnectionError(fail to connect to stripe)
        # Sample error: https://sentry.io/organizations/doordash/issues/910873408/?project=180553&referrer=slack
        except stripe_error.APIConnectionError as e:
            raise PGPConnectionError from e
        except stripe_error.StripeError as e:
            stripe_error_parser = StripeErrorParser(e)
            # Handle stripe rate limit error
            # Sample error: https://sentry.io/organizations/doordash/issues/933580084/?project=180553&referrer=slack
            if stripe_error_parser.code == StripeErrorCode.rate_limit:
                raise PGPRateLimitError from e
            # Handle stripe api error
            # Sample error: https://sentry.io/organizations/doordash/issues/1252146500/?project=180553&referrer=slack
            if stripe_error_parser.type == StripeErrorType.api_error:
                raise PGPApiError from e
            # Handle stripe instant payout card decline error
            # Sample error: https://sentry.io/organizations/doordash/issues/1245226384/?project=180553&referrer=slack
            if (
                stripe_error_parser.type == StripeErrorType.invalid_request_error
                and "unable to perform an instant payout to this card"
                in stripe_error_parser.message
            ):
                # Replace with Instant Payout Error after PR merged
                raise

    return wrapper
